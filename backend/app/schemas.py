from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ── Auth ──────────────────────────────────────────
class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Tasks ─────────────────────────────────────────
class SubtitleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    index: int
    start_time: float
    end_time: float
    text: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_path: str
    title: str
    status: str
    audio_path: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    subtitles: list[SubtitleOut] = []


class TaskCreateOut(BaseModel):
    id: int
    status: str


# ── Feedback ──────────────────────────────────────
class FeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    content: str
    created_at: datetime
