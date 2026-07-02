from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    APP_NAME: str = "God English"
    DATABASE_URL: str = "sqlite:///./god_english.db"
    JWT_SECRET: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    MEDIA_DIR: str = str(Path(__file__).parent.parent / "media")
    ALLOWED_EXTENSIONS: set[str] = {"mp3", "mp4", "wav", "webm", "m4a", "flac"}
    MAX_UPLOAD_SIZE_MB: int = 500
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
