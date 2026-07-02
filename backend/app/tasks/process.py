import os
from .celery_app import celery_app
from ..database import SessionLocal
from ..models import Task, Subtitle
from ..services.media import download_media, extract_audio
from ..services.asr import transcribe


@celery_app.task(bind=True, max_retries=2)
def process_task(self, task_id: int):
    """Celery task: downloads/extracts audio, runs ASR, saves subtitles."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        # Step 1: Get audio source
        if task.source_type == "url":
            video_path = download_media(task.source_path)
        else:
            video_path = task.source_path

        # Step 2: Extract audio to mp3
        audio_path = extract_audio(video_path)

        # Store relative path: <task_dir>/audio.mp3
        task_dir = os.path.basename(os.path.dirname(audio_path))
        task.audio_path = f"{task_dir}/audio.mp3"

        # Step 3: ASR transcription
        segments = transcribe(audio_path)

        # Step 4: Save subtitles
        for seg in segments:
            sub = Subtitle(
                task_id=task.id,
                index=seg["index"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"],
            )
            db.add(sub)

        task.status = "done"
        db.commit()
        return {"status": "done", "task_id": task_id, "segments": len(segments)}

    except Exception as exc:
        if task:
            task.status = "failed"
            task.error_msg = str(exc)[:500]
            db.commit()
        raise self.retry(exc=exc, countdown=60)

    finally:
        db.close()
