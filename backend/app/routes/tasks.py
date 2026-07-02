import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from ..models import User, Task
from ..schemas import TaskOut, TaskCreateOut
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(
        Task.id == task_id, Task.user_id == current_user.id
    ).first()
    if not task or not task.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")

    full_path = os.path.join(settings.MEDIA_DIR, task.audio_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")

    return FileResponse(full_path, media_type="audio/mpeg")
