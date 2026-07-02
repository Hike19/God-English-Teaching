import os
import uuid
from threading import Thread
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from ..models import User, Task, Subtitle
from ..schemas import TaskOut, TaskCreateOut
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.get("", response_model=list[TaskOut])
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .options(joinedload(Task.subtitles))
        .order_by(Task.created_at.desc())
        .all()
    )
    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .options(joinedload(Task.subtitles))
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(
        Task.id == task_id, Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.audio_path:
        full_path = os.path.join(settings.MEDIA_DIR, task.audio_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    db.delete(task)
    db.commit()


@router.get("/{task_id}/audio")
def get_audio(
    task_id: int,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    # Auth via query-param token (for <audio> tag which can't send headers)
    from ..auth import get_user_from_token
    user = get_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    task = db.query(Task).filter(
        Task.id == task_id, Task.user_id == user.id
    ).first()
    if not task or not task.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")

    full_path = os.path.join(settings.MEDIA_DIR, task.audio_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")

    ext = os.path.splitext(full_path)[1].lower()
    mime_map = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
        ".flac": "audio/flac", ".webm": "audio/webm", ".ogg": "audio/ogg",
    }
    return FileResponse(full_path, media_type=mime_map.get(ext, "audio/mpeg"))


@router.post("/upload", response_model=TaskCreateOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    task_dir = os.path.join(settings.MEDIA_DIR, uuid.uuid4().hex)
    os.makedirs(task_dir, exist_ok=True)
    safe_name = f"upload.{ext}"
    save_path = os.path.join(task_dir, safe_name)

    async with aiofiles.open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    task = Task(
        user_id=current_user.id,
        source_type="upload",
        source_path=save_path,
        title=file.filename or "untitled",
        status="processing",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    task_id = task.id

    def _process():
        from ..database import SessionLocal
        db2 = SessionLocal()
        try:
            from ..services.media import extract_audio
            from ..services.asr import transcribe

            audio_path = extract_audio(save_path)
            task_dir = os.path.basename(os.path.dirname(audio_path))
            audio_name = os.path.basename(audio_path)
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                t.audio_path = f"{task_dir}/{audio_name}"
                db2.commit()

            segments = transcribe(audio_path)
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                for seg in segments:
                    sub = Subtitle(
                        task_id=t.id, index=seg["index"],
                        start_time=seg["start_time"], end_time=seg["end_time"],
                        text=seg["text"],
                    )
                    db2.add(sub)
                t.status = "done"
                db2.commit()
        except Exception as e:
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                t.status = "failed"
                t.error_msg = str(e)[:500]
                db2.commit()
        finally:
            db2.close()
    Thread(target=_process, daemon=True).start()

    return TaskCreateOut(id=task.id, status=task.status)


@router.post("/url", response_model=TaskCreateOut, status_code=status.HTTP_201_CREATED)
def submit_url(
    url: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = Task(
        user_id=current_user.id,
        source_type="url",
        source_path=url,
        title=url,
        status="processing",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    task_id = task.id

    def _process():
        from ..database import SessionLocal
        db2 = SessionLocal()
        try:
            from ..services.media import download_media, extract_audio
            from ..services.asr import transcribe

            video_path = download_media(url)
            audio_path = extract_audio(video_path)
            task_dir = os.path.basename(os.path.dirname(audio_path))
            audio_name = os.path.basename(audio_path)
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                t.audio_path = f"{task_dir}/{audio_name}"
                db2.commit()

            segments = transcribe(audio_path)
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                for seg in segments:
                    sub = Subtitle(
                        task_id=t.id, index=seg["index"],
                        start_time=seg["start_time"], end_time=seg["end_time"],
                        text=seg["text"],
                    )
                    db2.add(sub)
                t.status = "done"
                db2.commit()
        except Exception as e:
            t = db2.query(Task).filter(Task.id == task_id).first()
            if t:
                t.status = "failed"
                t.error_msg = str(e)[:500]
                db2.commit()
        finally:
            db2.close()
    Thread(target=_process, daemon=True).start()

    return TaskCreateOut(id=task.id, status=task.status)
