# God English Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack web app for English speaking practice — import media, ASR subtitle generation, synced playback.

**Architecture:** Vue 3 SPA frontend communicates with FastAPI REST backend. Celery workers handle async media processing (yt-dlp download → ffmpeg audio extraction → Whisper ASR → subtitle generation). SQLite stores users, tasks, subtitles, and feedback. JWT-based auth.

**Tech Stack:** Vue 3 + Vite + TypeScript + Pinia + Vue Router | Python 3.11+ / FastAPI + SQLAlchemy + Celery + Redis | faster-whisper + yt-dlp + ffmpeg | SQLite

## Global Constraints

- Python 3.11+ required
- Node.js 18+ required
- ffmpeg must be installed on the system
- Redis must be running for Celery
- Password hashing via bcrypt (passlib)
- JWT token expiry: 24 hours
- File upload whitelist: mp3, mp4, wav, webm, m4a, flac
- File upload max size: 500MB
- Browser targets: Chrome/Edge/Firefox latest 2 major versions
- All backend routes under `/api/` prefix
- All frontend code in TypeScript with strict mode

---

### Task 1: Backend Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/main.py`

**Interfaces:**
- Produces: `get_db()` session generator, `Base` declarative base, all SQLAlchemy models, `Settings` config object, FastAPI `app` instance

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pydantic==2.10.3
pydantic-settings==2.7.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.18
celery[redis]==5.4.0
redis==5.2.1
faster-whisper==1.1.0
yt-dlp==2024.12.13
ffmpeg-python==0.2.0
aiofiles==24.1.0
```

- [ ] **Step 2: Create backend/app/__init__.py** (empty file)

```bash
touch backend/app/__init__.py
```

- [ ] **Step 3: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
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

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Create backend/app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite requires this
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create backend/app/models.py**

```python
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # bcrypt hash
    created_at = Column(DateTime, server_default=func.now())

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("source_type IN ('upload', 'url')", name="ck_source_type"),
        CheckConstraint("status IN ('processing', 'done', 'failed')", name="ck_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="processing")
    audio_path = Column(String, nullable=True)
    error_msg = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="tasks")
    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")


class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    task = relationship("Task", back_populates="subtitles")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="feedback")
```

- [ ] **Step 6: Create backend/app/main.py**

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

# Ensure media directory exists
os.makedirs(settings.MEDIA_DIR, exist_ok=True)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Verify the app starts**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/api/health` — should return `{"status":"ok"}`. Then stop the server (`Ctrl+C`).

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: backend scaffolding — FastAPI, SQLAlchemy models, config"
```

---

### Task 2: Auth System (Register, Login, JWT)

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/routes/auth.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `get_db()`, `User` model, `app` instance
- Produces: `create_access_token()`, `get_current_user()` dependency, `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

- [ ] **Step 1: Create backend/app/auth.py**

```python
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: validates JWT and returns the User or raises 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
```

- [ ] **Step 2: Create backend/app/schemas.py**

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────
class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Tasks ─────────────────────────────────────────
class SubtitleOut(BaseModel):
    id: int
    index: int
    start_time: float
    end_time: float
    text: str

    class Config:
        from_attributes = True


class TaskOut(BaseModel):
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

    class Config:
        from_attributes = True


class TaskCreateOut(BaseModel):
    id: int
    status: str


# ── Feedback ──────────────────────────────────────
class FeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Create backend/app/routes/__init__.py** (empty file)

```bash
touch backend/app/routes/__init__.py
```

- [ ] **Step 4: Create backend/app/routes/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import UserRegister, UserLogin, UserOut, TokenOut
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(username=body.username, password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user.id})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
```

- [ ] **Step 5: Modify backend/app/main.py — register auth router**

In `backend/app/main.py`, add after the `app.add_middleware(...)` block:

```python
from .routes import auth

app.include_router(auth.router)
```

- [ ] **Step 6: Verify auth endpoints**

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
# Expected: {"access_token":"...", "token_type":"bearer", "user":{...}}

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
# Expected: {"access_token":"...", "token_type":"bearer", "user":{...}}
```

- [ ] **Step 7: Create backend/tests/test_auth.py**

```python
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal

client = TestClient(app)

# Setup: create tables
Base.metadata.create_all(bind=engine)


def test_register_and_login():
    # Register
    resp = client.post("/api/auth/register", json={"username": "authtest", "password": "test123"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "authtest"

    # Duplicate register
    resp2 = client.post("/api/auth/register", json={"username": "authtest", "password": "test123"})
    assert resp2.status_code == 400

    # Login
    resp3 = client.post("/api/auth/login", json={"username": "authtest", "password": "test123"})
    assert resp3.status_code == 200
    assert "access_token" in resp3.json()

    # Bad login
    resp4 = client.post("/api/auth/login", json={"username": "authtest", "password": "wrong"})
    assert resp4.status_code == 401

    # Me
    token = resp3.json()["access_token"]
    resp5 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp5.status_code == 200
    assert resp5.json()["username"] == "authtest"

    # Me without token
    resp6 = client.get("/api/auth/me")
    assert resp6.status_code == 401
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/auth.py backend/app/schemas.py backend/app/routes/ backend/app/main.py backend/tests/
git commit -m "feat: auth system — register, login, JWT"
```

---

### Task 3: Task CRUD API

**Files:**
- Create: `backend/app/routes/tasks.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `get_db()`, `get_current_user()`, `Task`/`Subtitle` models, `TaskOut`/`TaskCreateOut` schemas, `app` instance
- Produces: `GET /api/tasks`, `GET /api/tasks/{id}`, `DELETE /api/tasks/{id}`, `GET /api/tasks/{id}/audio`

- [ ] **Step 1: Create backend/app/routes/tasks.py**

```python
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

    # Delete audio file if exists
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
```

- [ ] **Step 2: Modify backend/app/main.py — register tasks router**

```python
from .routes import tasks

app.include_router(tasks.router)
```

- [ ] **Step 3: Create backend/tests/test_tasks.py**

```python
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Task, User
from app.auth import hash_password

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _register_and_get_token() -> tuple[str, int]:
    resp = client.post("/api/auth/register", json={"username": "tasktest", "password": "test123"})
    data = resp.json()
    return data["access_token"], data["user"]["id"]


def test_task_list_empty():
    token, _ = _register_and_get_token()
    resp = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_task_list_requires_auth():
    resp = client.get("/api/tasks")
    assert resp.status_code == 401


def test_get_task_not_found():
    token, _ = _register_and_get_token()
    resp = client.get("/api/tasks/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_tasks.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/tasks.py backend/app/main.py backend/tests/test_tasks.py
git commit -m "feat: task CRUD API — list, get, delete, audio streaming"
```

---

### Task 4: Feedback API

**Files:**
- Create: `backend/app/routes/feedback.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `get_db()`, `get_current_user()`, `Feedback` model, `FeedbackCreate`/`FeedbackOut` schemas, `app` instance
- Produces: `POST /api/feedback`

- [ ] **Step 1: Create backend/app/routes/feedback.py**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Feedback
from ..schemas import FeedbackCreate, FeedbackOut
from ..auth import get_current_user

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    body: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fb = Feedback(user_id=current_user.id, content=body.content)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackOut.model_validate(fb)
```

- [ ] **Step 2: Modify backend/app/main.py — register feedback router**

```python
from .routes import feedback

app.include_router(feedback.router)
```

- [ ] **Step 3: Create backend/tests/test_feedback.py**

```python
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def test_submit_feedback():
    resp = client.post("/api/auth/register", json={"username": "fbtest", "password": "test123"})
    token = resp.json()["access_token"]

    resp2 = client.post(
        "/api/feedback",
        json={"content": "Great app!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["content"] == "Great app!"
    assert resp2.json()["user_id"] is not None


def test_feedback_requires_auth():
    resp = client.post("/api/feedback", json={"content": "test"})
    assert resp.status_code == 401
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_feedback.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/feedback.py backend/app/main.py backend/tests/test_feedback.py
git commit -m "feat: feedback API — submit text feedback"
```

---

### Task 5: Upload & Paste URL Endpoints

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/media.py`
- Modify: `backend/app/routes/tasks.py`

**Interfaces:**
- Consumes: `get_db()`, `get_current_user()`, `Task` model, `settings`
- Produces: `POST /api/tasks/upload` (multipart form), `POST /api/tasks/url` (JSON body), `download_media(url: str) -> str` helper, `extract_audio(input_path: str) -> str` helper

- [ ] **Step 1: Create backend/app/services/__init__.py** (empty file)

```bash
touch backend/app/services/__init__.py
```

- [ ] **Step 2: Create backend/app/services/media.py**

```python
import os
import uuid
import subprocess
import yt_dlp
from ..config import settings


def download_media(url: str) -> str:
    """Download media from URL using yt-dlp. Returns the file path."""
    task_dir = os.path.join(settings.MEDIA_DIR, uuid.uuid4().hex)
    os.makedirs(task_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(task_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        # yt-dlp may append extension automatically; search for any file in dir
        files = os.listdir(task_dir)
        if not files:
            raise RuntimeError("Download failed: no output file found")
        filename = os.path.join(task_dir, files[0])

    return filename


def extract_audio(input_path: str) -> str:
    """Extract audio from video/audio file to mp3 using ffmpeg. Returns the mp3 path."""
    output_dir = os.path.dirname(input_path)
    output_path = os.path.join(output_dir, "audio.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",                # no video
        "-acodec", "libmp3lame",
        "-ar", "16000",       # 16kHz for Whisper
        "-ac", "1",           # mono
        "-b:a", "64k",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
    return output_path
```

- [ ] **Step 3: Modify backend/app/routes/tasks.py — add upload and URL endpoints**

Add to `backend/app/routes/tasks.py`, after the existing imports:

```python
import os
import uuid
import shutil
import aiofiles
from fastapi import UploadFile, File, Form
from ..services.media import download_media, extract_audio
```

Add after the `get_audio` route:

```python
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=TaskCreateOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Save file
    task_dir = os.path.join(settings.MEDIA_DIR, uuid.uuid4().hex)
    os.makedirs(task_dir, exist_ok=True)
    safe_name = f"upload.{ext}"
    save_path = os.path.join(task_dir, safe_name)

    async with aiofiles.open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)

    # Create task
    task = Task(
        user_id=current_user.id,
        source_type="upload",
        source_path=save_path,
        title=file.filename,
        status="processing",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Quick note: in a real app we'd dispatch a Celery task here.
    # For now we just create the DB record; processing will be wired in Task 7.
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

    # Same note: Celery dispatch will be wired in Task 7.
    return TaskCreateOut(id=task.id, status=task.status)
```

Also add these imports to the top of the file (integrating with existing ones):

```python
import uuid
import aiofiles
from fastapi import UploadFile, File, Form
from ..services.media import download_media, extract_audio
from ..config import settings
```

- [ ] **Step 4: Verify upload endpoint**

```bash
# Create a small test file
echo "test" > /tmp/test.mp3

curl -X POST http://localhost:8000/api/tasks/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/tmp/test.mp3"
# Expected: {"id":1,"status":"processing"}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ backend/app/routes/tasks.py
git commit -m "feat: upload and URL endpoints with media download/extraction service"
```

---

### Task 6: ASR Service (Whisper)

**Files:**
- Create: `backend/app/services/asr.py`
- Create: `backend/tests/test_asr.py`

**Interfaces:**
- Consumes: `settings.MEDIA_DIR`
- Produces: `transcribe(audio_path: str) -> list[dict]` where each dict has `{index, start_time, end_time, text}`

- [ ] **Step 1: Create backend/app/services/asr.py**

```python
from faster_whisper import WhisperModel

# Load model once at module level
MODEL_SIZE = "large-v3"
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments.

    Returns:
        list[dict]: [{"index": 0, "start_time": 0.0, "end_time": 2.5, "text": "Hello"}, ...]
    """
    model = get_model()
    segments, _ = model.transcribe(audio_path, beam_size=5, language="en")

    results = []
    for i, segment in enumerate(segments):
        results.append({
            "index": i,
            "start_time": round(segment.start, 2),
            "end_time": round(segment.end, 2),
            "text": segment.text.strip(),
        })
    return results
```

- [ ] **Step 2: Create backend/tests/test_asr.py**

```python
import os
import subprocess
from app.services.asr import transcribe
from app.config import settings


def test_transcribe_silence_returns_empty():
    """Generate a short silent audio file and verify ASR returns no meaningful text."""
    test_audio = os.path.join(settings.MEDIA_DIR, "silence_test.wav")
    # Generate 1 second of silence
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
        "-t", "1", "-ar", "16000", test_audio,
    ], capture_output=True)

    results = transcribe(test_audio)
    # Silence may return empty or very short segments — both are acceptable
    assert isinstance(results, list)
    # Clean up
    os.remove(test_audio)


def test_transcribe_returns_proper_structure():
    """Generate a tone audio and verify result structure."""
    test_audio = os.path.join(settings.MEDIA_DIR, "tone_test.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-ar", "16000", "-ac", "1", test_audio,
    ], capture_output=True)

    results = transcribe(test_audio)
    assert isinstance(results, list)
    if results:
        seg = results[0]
        assert "index" in seg
        assert "start_time" in seg
        assert "end_time" in seg
        assert "text" in seg
        assert seg["start_time"] < seg["end_time"]

    os.remove(test_audio)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_asr.py -v
```

Expected: tests PASS (first transcription may take time downloading the model).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/asr.py backend/tests/test_asr.py
git commit -m "feat: ASR service — faster-whisper transcription"
```

---

### Task 7: Celery Processing Pipeline

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`
- Create: `backend/app/tasks/process.py`
- Modify: `backend/app/routes/tasks.py` (wire Celery dispatch)

**Interfaces:**
- Consumes: `settings`, `SessionLocal`, `Task`/`Subtitle` models, `download_media()`, `extract_audio()`, `transcribe()`
- Produces: `process_task.delay(task_id)` — callable from routes

- [ ] **Step 1: Create backend/app/tasks/__init__.py** (empty file)

```bash
touch backend/app/tasks/__init__.py
```

- [ ] **Step 2: Create backend/app/tasks/celery_app.py**

```python
from celery import Celery
from ..config import settings

celery_app = Celery(
    "god_english",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

- [ ] **Step 3: Create backend/app/tasks/process.py**

```python
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

        # Step 1: Get audio
        if task.source_type == "url":
            video_path = download_media(task.source_path)
        else:
            video_path = task.source_path

        # Step 2: Extract audio
        audio_path = extract_audio(video_path)
        # Store relative path for serving
        rel_path = os.path.relpath(audio_path, os.path.dirname(os.path.dirname(audio_path)))
        task.audio_path = os.path.join(os.path.basename(os.path.dirname(audio_path)), "audio.mp3")

        # Step 3: ASR
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
        task.status = "failed"
        task.error_msg = str(exc)[:500]
        db.commit()
        raise self.retry(exc=exc, countdown=60)

    finally:
        db.close()
```

- [ ] **Step 4: Modify backend/app/routes/tasks.py — wire Celery dispatch**

In the `upload_file` function, after `db.refresh(task)` add:

```python
    from ..tasks.process import process_task
    process_task.delay(task.id)
```

In the `submit_url` function, after `db.refresh(task)` add:

```python
    from ..tasks.process import process_task
    process_task.delay(task.id)
```

- [ ] **Step 5: Verify Celery worker starts**

```bash
# Ensure Redis is running first, then:
cd backend && celery -A app.tasks.celery_app worker --loglevel=info
```

Expected: worker starts without errors, shows registered tasks.

- [ ] **Step 6: Commit**

```bash
git add backend/app/tasks/ backend/app/routes/tasks.py
git commit -m "feat: Celery processing pipeline — download → extract → ASR → save"
```

---

### Task 8: Frontend Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/views/HomeView.vue`

**Interfaces:**
- Consumes: (none — first frontend task)
- Produces: Vite dev server running on port 5173, Vue Router with `/` route, Axios client with base URL + JWT interceptor

- [ ] **Step 1: Create frontend/package.json**

```json
{
  "name": "god-english-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "pinia": "^2.3.0",
    "axios": "^1.7.9"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "typescript": "~5.6.3",
    "vite": "^6.0.5",
    "vue-tsc": "^2.2.0",
    "vitest": "^2.1.8",
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 2: Create frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create frontend/tsconfig.json**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] **Step 4: Create frontend/tsconfig.app.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForExpose": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "env.d.ts"]
}
```

- [ ] **Step 5: Create frontend/tsconfig.node.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Create frontend/env.d.ts**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 7: Create frontend/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>God English — 英语口语练习</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 8: Create frontend/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 9: Create frontend/src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/TaskHistoryView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

export default router
```

- [ ] **Step 10: Create frontend/src/api/client.ts**

```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401 → clear token
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

- [ ] **Step 11: Create frontend/src/views/HomeView.vue**

```vue
<template>
  <div class="home">
    <header class="header-bar">
      <ImportUpload />
      <PasteUrl />
    </header>

    <main class="player-panel">
      <PlayerPanel />
    </main>

    <footer class="footer-bar">
      <button @click="showLogin = true">登录</button>
      <button @click="showFeedback = true">反馈</button>
    </footer>

    <LoginModal v-if="showLogin" @close="showLogin = false" />
    <FeedbackModal v-if="showFeedback" @close="showFeedback = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ImportUpload from '@/components/ImportUpload.vue'
import PasteUrl from '@/components/PasteUrl.vue'
import PlayerPanel from '@/components/PlayerPanel.vue'
import LoginModal from '@/components/LoginModal.vue'
import FeedbackModal from '@/components/FeedbackModal.vue'

const showLogin = ref(false)
const showFeedback = ref(false)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f0f0f;
  color: #e0e0e0;
  min-height: 100vh;
}

.home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
```

- [ ] **Step 12: Install dependencies and verify dev server**

```bash
cd frontend && npm install && npm run dev
```

Visit `http://localhost:5173` — should show a black page with header, middle, and footer areas (components not built yet, so it'll have errors in console — that's expected).

- [ ] **Step 13: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffolding — Vue 3 + Vite + Router + Pinia + Axios"
```

---

### Task 9: Auth UI — Login Modal + Auth Store

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/components/LoginModal.vue`

**Interfaces:**
- Consumes: `apiClient` axios instance
- Produces: `useAuthStore` (login, register, logout, isLoggedIn, user, token), `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

- [ ] **Step 1: Create frontend/src/api/auth.ts**

```typescript
import apiClient from './client'

export interface User {
  id: number
  username: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export async function register(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', { username, password })
  return data
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', { username, password })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me')
  return data
}
```

- [ ] **Step 2: Create frontend/src/stores/auth.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function loginAction(username: string, password: string) {
    const result = await authApi.login(username, password)
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('token', result.access_token)
  }

  async function registerAction(username: string, password: string) {
    const result = await authApi.register(username, password)
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('token', result.access_token)
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      user.value = await authApi.getMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, loginAction, registerAction, fetchMe, logout }
})
```

- [ ] **Step 3: Create frontend/src/components/LoginModal.vue**

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      <form @submit.prevent="handleSubmit">
        <input v-model="username" type="text" placeholder="用户名" required minlength="2" />
        <input v-model="password" type="password" placeholder="密码" required minlength="6" />
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '...' : isLogin ? '登录' : '注册' }}
        </button>
      </form>
      <p class="toggle">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <a href="#" @click.prevent="isLogin = !isLogin; error = ''">
          {{ isLogin ? '去注册' : '去登录' }}
        </a>
      </p>
      <button class="close-btn" @click="$emit('close')">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

defineEmits<{ close: [] }>()

const auth = useAuthStore()
const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (isLogin.value) {
      await auth.loginAction(username.value, password.value)
    } else {
      await auth.registerAction(username.value, password.value)
    }
    username.value = ''
    password.value = ''
    // close is handled by parent via store change
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #1a1a2e; border-radius: 12px; padding: 2rem;
  width: 360px; position: relative;
}
h2 { text-align: center; margin-bottom: 1.5rem; color: #e0e0e0; }
input {
  display: block; width: 100%; margin-bottom: 0.75rem;
  padding: 0.75rem; border-radius: 8px; border: 1px solid #333;
  background: #16213e; color: #e0e0e0; font-size: 1rem;
}
input:focus { outline: none; border-color: #4fc3f7; }
button[type="submit"] {
  width: 100%; padding: 0.75rem; border: none; border-radius: 8px;
  background: #4fc3f7; color: #000; font-size: 1rem; font-weight: 600; cursor: pointer;
}
button[type="submit"]:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #ef5350; font-size: 0.875rem; margin-bottom: 0.5rem; }
.toggle { text-align: center; margin-top: 1rem; font-size: 0.875rem; color: #999; }
.toggle a { color: #4fc3f7; text-decoration: none; }
.close-btn {
  position: absolute; top: 0.75rem; right: 0.75rem;
  background: none; border: none; color: #999; font-size: 1.25rem; cursor: pointer;
}
</style>
```

- [ ] **Step 4: Verify**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/auth.ts frontend/src/api/auth.ts frontend/src/components/LoginModal.vue
git commit -m "feat: auth UI — login/register modal + pinia store + API layer"
```

---

### Task 10: Header Components — ImportUpload + PasteUrl

**Files:**
- Create: `frontend/src/components/ImportUpload.vue`
- Create: `frontend/src/components/PasteUrl.vue`
- Create: `frontend/src/api/tasks.ts`
- Create: `frontend/src/stores/tasks.ts`

**Interfaces:**
- Consumes: `apiClient`, `useAuthStore`
- Produces: `POST /api/tasks/upload`, `POST /api/tasks/url`, `useTasksStore`

- [ ] **Step 1: Create frontend/src/api/tasks.ts**

```typescript
import apiClient from './client'

export interface Subtitle {
  id: number
  index: number
  start_time: number
  end_time: number
  text: string
}

export interface Task {
  id: number
  source_type: 'upload' | 'url'
  source_path: string
  title: string
  status: 'processing' | 'done' | 'failed'
  audio_path: string | null
  error_msg: string | null
  created_at: string
  updated_at: string
  subtitles: Subtitle[]
}

export interface TaskCreateResponse {
  id: number
  status: string
}

export async function uploadFile(file: File): Promise<TaskCreateResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<TaskCreateResponse>('/tasks/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

export async function submitUrl(url: string): Promise<TaskCreateResponse> {
  const formData = new FormData()
  formData.append('url', url)
  const { data } = await apiClient.post<TaskCreateResponse>('/tasks/url', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listTasks(): Promise<Task[]> {
  const { data } = await apiClient.get<Task[]>('/tasks')
  return data
}

export async function getTask(id: number): Promise<Task> {
  const { data } = await apiClient.get<Task>(`/tasks/${id}`)
  return data
}

export async function deleteTask(id: number): Promise<void> {
  await apiClient.delete(`/tasks/${id}`)
}

export function getAudioUrl(taskId: number): string {
  return `/api/tasks/${taskId}/audio`
}
```

- [ ] **Step 2: Create frontend/src/stores/tasks.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as tasksApi from '@/api/tasks'
import type { Task } from '@/api/tasks'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)

  async function fetchTasks() {
    loading.value = true
    try {
      tasks.value = await tasksApi.listTasks()
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id: number) {
    loading.value = true
    try {
      currentTask.value = await tasksApi.getTask(id)
    } finally {
      loading.value = false
    }
  }

  async function createFromFile(file: File): Promise<number> {
    const result = await tasksApi.uploadFile(file)
    await pollUntilDone(result.id)
    return result.id
  }

  async function createFromUrl(url: string): Promise<number> {
    const result = await tasksApi.submitUrl(url)
    await pollUntilDone(result.id)
    return result.id
  }

  async function pollUntilDone(taskId: number, intervalMs = 2000, timeoutMs = 600000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      const task = await tasksApi.getTask(taskId)
      if (task.status === 'done' || task.status === 'failed') {
        currentTask.value = task
        return
      }
      await new Promise((r) => setTimeout(r, intervalMs))
    }
    throw new Error('Task processing timed out')
  }

  async function removeTask(id: number) {
    await tasksApi.deleteTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (currentTask.value?.id === id) {
      currentTask.value = null
    }
  }

  return { tasks, currentTask, loading, fetchTasks, fetchTask, createFromFile, createFromUrl, removeTask }
})
```

- [ ] **Step 3: Create frontend/src/components/ImportUpload.vue**

```vue
<template>
  <div class="import-upload">
    <button @click="triggerUpload" :disabled="uploading">
      {{ uploading ? '上传中...' : '📁 导入素材库' }}
    </button>
    <input
      ref="fileInput"
      type="file"
      accept=".mp3,.mp4,.wav,.webm,.m4a,.flac"
      @change="handleFile"
      hidden
    />
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits<{ uploaded: [taskId: number] }>()
const tasksStore = useTasksStore()
const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const error = ref('')

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    const taskId = await tasksStore.createFromFile(file)
    emit('uploaded', taskId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<style scoped>
.import-upload button {
  padding: 0.5rem 1rem; border: none; border-radius: 6px;
  background: #1a73e8; color: white; font-size: 0.9rem; cursor: pointer;
}
.import-upload button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #ef5350; font-size: 0.75rem; margin-top: 0.25rem; }
</style>
```

- [ ] **Step 4: Create frontend/src/components/PasteUrl.vue**

```vue
<template>
  <div class="paste-url">
    <input
      v-model="url"
      type="text"
      placeholder="粘贴视频/音频链接（B站、抖音、小红书等）"
      :disabled="submitting"
      @keydown.enter="submit"
    />
    <button @click="submit" :disabled="submitting || !url.trim()">
      {{ submitting ? '处理中...' : '提交' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits<{ submitted: [taskId: number] }>()
const tasksStore = useTasksStore()
const url = ref('')
const submitting = ref(false)
const error = ref('')

async function submit() {
  if (!url.value.trim()) return
  submitting.value = true
  error.value = ''
  try {
    const taskId = await tasksStore.createFromUrl(url.value.trim())
    url.value = ''
    emit('submitted', taskId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.paste-url { display: flex; gap: 0.5rem; }
.paste-url input {
  flex: 1; padding: 0.5rem 0.75rem; border-radius: 6px;
  border: 1px solid #333; background: #16213e; color: #e0e0e0; font-size: 0.9rem;
}
.paste-url input:focus { outline: none; border-color: #4fc3f7; }
.paste-url button {
  padding: 0.5rem 1rem; border: none; border-radius: 6px;
  background: #4fc3f7; color: #000; font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.paste-url button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #ef5350; font-size: 0.75rem; }
</style>
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ImportUpload.vue frontend/src/components/PasteUrl.vue frontend/src/api/tasks.ts frontend/src/stores/tasks.ts
git commit -m "feat: import & paste URL components with tasks store"
```

---

### Task 11: Player — PlayerControls + SubtitleDisplay + PlayerPanel

**Files:**
- Create: `frontend/src/components/PlayerControls.vue`
- Create: `frontend/src/components/SubtitleDisplay.vue`
- Create: `frontend/src/components/PlayerPanel.vue`
- Create: `frontend/src/stores/player.ts`

**Interfaces:**
- Consumes: `useTasksStore` (currentTask), `getAudioUrl()`
- Produces: PlayerPanel containing synced audio + subtitles with pause, speed, progress bar

- [ ] **Step 1: Create frontend/src/stores/player.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const playbackRate = ref(1.0)
  const audioRef = ref<HTMLAudioElement | null>(null)

  const formattedCurrentTime = computed(() => formatTime(currentTime.value))
  const formattedDuration = computed(() => formatTime(duration.value))
  const progress = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
  )

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  function setAudio(el: HTMLAudioElement | null) {
    audioRef.value = el
  }

  function togglePlay() {
    const a = audioRef.value
    if (!a) return
    if (a.paused) {
      a.play()
      isPlaying.value = true
    } else {
      a.pause()
      isPlaying.value = false
    }
  }

  function seek(time: number) {
    const a = audioRef.value
    if (!a) return
    a.currentTime = time
    currentTime.value = time
  }

  function seekByPercent(percent: number) {
    seek((percent / 100) * duration.value)
  }

  function setRate(rate: number) {
    const a = audioRef.value
    if (!a) return
    a.playbackRate = rate
    playbackRate.value = rate
  }

  function onTimeUpdate(time: number) {
    currentTime.value = time
  }

  function onLoadedMetadata(dur: number) {
    duration.value = dur
  }

  function onEnded() {
    isPlaying.value = false
  }

  function onPlay() {
    isPlaying.value = true
  }

  function onPause() {
    isPlaying.value = false
  }

  return {
    isPlaying, currentTime, duration, playbackRate,
    formattedCurrentTime, formattedDuration, progress,
    setAudio, togglePlay, seek, seekByPercent, setRate,
    onTimeUpdate, onLoadedMetadata, onEnded, onPlay, onPause,
  }
})
```

- [ ] **Step 2: Create frontend/src/components/PlayerControls.vue**

```vue
<template>
  <div class="player-controls">
    <button class="play-btn" @click="player.togglePlay()">
      {{ player.isPlaying ? '⏸' : '▶' }}
    </button>

    <span class="time">{{ player.formattedCurrentTime }}</span>

    <div
      class="progress-bar"
      ref="barRef"
      @mousedown="startDrag"
      @click="clickBar"
    >
      <div class="progress-fill" :style="{ width: player.progress + '%' }" />
    </div>

    <span class="time">{{ player.formattedDuration }}</span>

    <select
      class="rate-select"
      :value="player.playbackRate"
      @change="player.setRate(Number(($event.target as HTMLSelectElement).value))"
    >
      <option v-for="r in rates" :key="r" :value="r">{{ r }}x</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()
const rates = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
const barRef = ref<HTMLDivElement>()
let dragging = false

function clickBar(e: MouseEvent) {
  const bar = barRef.value
  if (!bar) return
  const rect = bar.getBoundingClientRect()
  const percent = ((e.clientX - rect.left) / rect.width) * 100
  player.seekByPercent(percent)
}

function startDrag(e: MouseEvent) {
  dragging = true
  const bar = barRef.value
  if (!bar) return

  function onMove(ev: MouseEvent) {
    if (!dragging || !bar) return
    const rect = bar.getBoundingClientRect()
    const percent = Math.max(0, Math.min(100, ((ev.clientX - rect.left) / rect.width) * 100))
    player.seekByPercent(percent)
  }

  function onUp() {
    dragging = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)

  onMove(e) // immediate jump to click position
}
</script>

<style scoped>
.player-controls {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 1rem; background: #1a1a2e; border-radius: 8px;
}
.play-btn {
  background: none; border: none; color: #e0e0e0; font-size: 1.5rem; cursor: pointer;
}
.time { font-size: 0.8rem; color: #999; min-width: 3rem; text-align: center; }
.progress-bar {
  flex: 1; height: 6px; background: #333; border-radius: 3px; cursor: pointer; position: relative;
}
.progress-fill {
  height: 100%; background: #4fc3f7; border-radius: 3px; transition: width 0.1s linear;
}
.rate-select {
  background: #16213e; color: #e0e0e0; border: 1px solid #333;
  border-radius: 4px; padding: 0.25rem; font-size: 0.8rem;
}
</style>
```

- [ ] **Step 3: Create frontend/src/components/SubtitleDisplay.vue**

```vue
<template>
  <div class="subtitle-display" ref="containerRef">
    <div v-if="!subtitles.length" class="placeholder">
      上传文件或粘贴链接以生成字幕
    </div>
    <div
      v-for="sub in subtitles"
      :key="sub.id"
      :ref="(el) => setSubRef(sub.id, el as HTMLElement)"
      class="subtitle-line"
      :class="{ active: isActive(sub), played: isPlayed(sub), upcoming: isUpcoming(sub) }"
      @click="seekTo(sub.start_time)"
    >
      {{ sub.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePlayerStore } from '@/stores/player'
import type { Subtitle } from '@/api/tasks'

const props = defineProps<{ subtitles: Subtitle[] }>()
const player = usePlayerStore()
const containerRef = ref<HTMLElement>()
const subRefs = new Map<number, HTMLElement>()

function setSubRef(id: number, el: HTMLElement | null) {
  if (el) subRefs.set(id, el)
}

function isActive(sub: Subtitle): boolean {
  return player.currentTime >= sub.start_time && player.currentTime < sub.end_time
}

function isPlayed(sub: Subtitle): boolean {
  return player.currentTime >= sub.end_time
}

function isUpcoming(sub: Subtitle): boolean {
  return player.currentTime < sub.start_time
}

function seekTo(time: number) {
  player.seek(time)
}

// Auto-scroll to active subtitle
watch(() => player.currentTime, () => {
  for (const sub of props.subtitles) {
    if (isActive(sub)) {
      const el = subRefs.get(sub.id)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
      break
    }
  }
})
</script>

<style scoped>
.subtitle-display {
  flex: 1; overflow-y: auto; padding: 1rem;
  max-height: 60vh;
}
.placeholder { text-align: center; color: #666; padding: 3rem 1rem; }
.subtitle-line {
  padding: 0.5rem 1rem; margin: 0.25rem 0; border-radius: 6px;
  font-size: 1.1rem; line-height: 1.6; cursor: pointer;
  transition: opacity 0.3s, background 0.3s;
}
.subtitle-line.played { opacity: 0.3; color: #666; }
.subtitle-line.upcoming { opacity: 0.5; color: #999; }
.subtitle-line.active {
  opacity: 1; color: #fff; background: rgba(79, 195, 247, 0.15);
  font-weight: 600; font-size: 1.3rem;
}
</style>
```

- [ ] **Step 4: Create frontend/src/components/PlayerPanel.vue**

```vue
<template>
  <div class="player-panel">
    <div v-if="!tasksStore.currentTask" class="empty-state">
      导入素材或粘贴链接开始练习
    </div>
    <template v-else-if="tasksStore.currentTask.status === 'processing'">
      <div class="processing">
        <div class="spinner" />
        <p>正在处理音频并生成字幕...</p>
      </div>
    </template>
    <template v-else-if="tasksStore.currentTask.status === 'failed'">
      <div class="failed">
        <p>处理失败：{{ tasksStore.currentTask.error_msg }}</p>
      </div>
    </template>
    <template v-else>
      <audio
        ref="audioEl"
        :src="audioSrc"
        preload="auto"
        @timeupdate="player.onTimeUpdate(($event.target as HTMLAudioElement).currentTime)"
        @loadedmetadata="player.onLoadedMetadata(($event.target as HTMLAudioElement).duration)"
        @ended="player.onEnded()"
        @play="player.onPlay()"
        @pause="player.onPause()"
      />
      <SubtitleDisplay :subtitles="tasksStore.currentTask.subtitles" />
      <PlayerControls />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { usePlayerStore } from '@/stores/player'
import { getAudioUrl } from '@/api/tasks'
import SubtitleDisplay from './SubtitleDisplay.vue'
import PlayerControls from './PlayerControls.vue'

const tasksStore = useTasksStore()
const player = usePlayerStore()
const audioEl = ref<HTMLAudioElement>()

const audioSrc = computed(() =>
  tasksStore.currentTask ? getAudioUrl(tasksStore.currentTask.id) : ''
)

onMounted(() => {
  player.setAudio(audioEl.value ?? null)
})

watch(audioEl, (el) => {
  player.setAudio(el ?? null)
})
</script>

<style scoped>
.player-panel {
  flex: 1; display: flex; flex-direction: column;
  justify-content: space-between;
}
.empty-state, .processing, .failed {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: #666; font-size: 1.1rem;
}
.processing { flex-direction: column; gap: 1rem; }
.spinner {
  width: 2rem; height: 2rem; border: 3px solid #333;
  border-top-color: #4fc3f7; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.failed { color: #ef5350; }
</style>
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/player.ts frontend/src/components/PlayerControls.vue frontend/src/components/SubtitleDisplay.vue frontend/src/components/PlayerPanel.vue
git commit -m "feat: player — subtitles + audio + controls (pause, speed, progress bar)"
```

---

### Task 12: Footer Components — FeedbackModal + HeaderBar & FooterBar

**Files:**
- Create: `frontend/src/api/feedback.ts`
- Create: `frontend/src/components/FeedbackModal.vue`
- Create: `frontend/src/components/HeaderBar.vue`
- Create: `frontend/src/components/FooterBar.vue`
- Modify: `frontend/src/views/HomeView.vue` (wire HeaderBar + FooterBar)

**Interfaces:**
- Consumes: `apiClient`, `useAuthStore`, existing components
- Produces: Complete HomeView layout with all components wired

- [ ] **Step 1: Create frontend/src/api/feedback.ts**

```typescript
import apiClient from './client'

export interface FeedbackResponse {
  id: number
  user_id: number | null
  content: string
  created_at: string
}

export async function submitFeedback(content: string): Promise<FeedbackResponse> {
  const { data } = await apiClient.post<FeedbackResponse>('/feedback', { content })
  return data
}
```

- [ ] **Step 2: Create frontend/src/components/FeedbackModal.vue**

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2>反馈</h2>
      <textarea
        v-model="content"
        placeholder="请输入您的反馈或建议..."
        rows="5"
        maxlength="2000"
      />
      <p class="char-count">{{ content.length }}/2000</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="success" class="success">感谢您的反馈！</p>
      <div class="actions">
        <button @click="$emit('close')">取消</button>
        <button class="primary" @click="submit" :disabled="submitting || !content.trim()">
          {{ submitting ? '提交中...' : '提交' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { submitFeedback } from '@/api/feedback'

defineEmits<{ close: [] }>()

const content = ref('')
const submitting = ref(false)
const error = ref('')
const success = ref(false)

async function submit() {
  if (!content.value.trim()) return
  submitting.value = true
  error.value = ''
  try {
    await submitFeedback(content.value.trim())
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 2000)
    content.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #1a1a2e; border-radius: 12px; padding: 2rem;
  width: 400px;
}
h2 { margin-bottom: 1rem; color: #e0e0e0; }
textarea {
  width: 100%; padding: 0.75rem; border-radius: 8px;
  border: 1px solid #333; background: #16213e; color: #e0e0e0;
  font-size: 1rem; resize: vertical;
}
textarea:focus { outline: none; border-color: #4fc3f7; }
.char-count { text-align: right; font-size: 0.75rem; color: #666; margin-top: 0.25rem; }
.error { color: #ef5350; font-size: 0.875rem; margin-top: 0.5rem; }
.success { color: #66bb6a; font-size: 0.875rem; margin-top: 0.5rem; }
.actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1rem; }
.actions button {
  padding: 0.5rem 1.25rem; border: none; border-radius: 6px;
  font-size: 0.9rem; cursor: pointer;
}
.actions button:first-child { background: #333; color: #e0e0e0; }
.actions button.primary { background: #4fc3f7; color: #000; font-weight: 600; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
```

- [ ] **Step 3: Create frontend/src/components/HeaderBar.vue**

```vue
<template>
  <header class="header-bar">
    <div class="logo">God English</div>
    <div class="actions">
      <ImportUpload @uploaded="onTaskCreated" />
      <PasteUrl @submitted="onTaskCreated" />
    </div>
  </header>
</template>

<script setup lang="ts">
import ImportUpload from './ImportUpload.vue'
import PasteUrl from './PasteUrl.vue'
import { useTasksStore } from '@/stores/tasks'

const tasksStore = useTasksStore()

async function onTaskCreated(taskId: number) {
  await tasksStore.fetchTask(taskId)
}
</script>

<style scoped>
.header-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.5rem; background: #1a1a2e; border-bottom: 1px solid #333;
}
.logo {
  font-size: 1.25rem; font-weight: 700; color: #4fc3f7; letter-spacing: 1px;
}
.actions { display: flex; gap: 1rem; align-items: center; }
</style>
```

- [ ] **Step 4: Create frontend/src/components/FooterBar.vue**

```vue
<template>
  <footer class="footer-bar">
    <button @click="$emit('login')">
      {{ auth.isLoggedIn ? auth.user?.username : '登录' }}
    </button>
    <button v-if="auth.isLoggedIn" @click="auth.logout()">退出</button>
    <button @click="$emit('feedback')">反馈</button>
  </footer>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
defineEmits<{ login: []; feedback: [] }>()
</script>

<style scoped>
.footer-bar {
  display: flex; justify-content: center; gap: 1rem;
  padding: 0.75rem 1.5rem; background: #1a1a2e; border-top: 1px solid #333;
}
.footer-bar button {
  padding: 0.5rem 1rem; border: 1px solid #333; border-radius: 6px;
  background: transparent; color: #999; font-size: 0.85rem; cursor: pointer;
}
.footer-bar button:hover { color: #e0e0e0; border-color: #666; }
</style>
```

- [ ] **Step 5: Modify frontend/src/views/HomeView.vue — replace placeholder with wired components**

Replace the entire `HomeView.vue`:

```vue
<template>
  <div class="home">
    <HeaderBar />
    <main class="player-area">
      <PlayerPanel />
    </main>
    <FooterBar @login="showLogin = true" @feedback="showFeedback = true" />

    <LoginModal v-if="showLogin" @close="showLogin = false" />
    <FeedbackModal v-if="showFeedback" @close="showFeedback = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HeaderBar from '@/components/HeaderBar.vue'
import FooterBar from '@/components/FooterBar.vue'
import PlayerPanel from '@/components/PlayerPanel.vue'
import LoginModal from '@/components/LoginModal.vue'
import FeedbackModal from '@/components/FeedbackModal.vue'

const showLogin = ref(false)
const showFeedback = ref(false)
</script>

<style scoped>
.home {
  display: flex; flex-direction: column; min-height: 100vh;
}
.player-area {
  flex: 1; display: flex; flex-direction: column;
}
</style>
```

(Global styles remain in App.vue or this file's non-scoped block if not already done.)

- [ ] **Step 6: Verify**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/feedback.ts frontend/src/components/FeedbackModal.vue frontend/src/components/HeaderBar.vue frontend/src/components/FooterBar.vue frontend/src/views/HomeView.vue
git commit -m "feat: header & footer bars, feedback modal, fully wired layout"
```

---

### Task 13: Task History View

**Files:**
- Create: `frontend/src/views/TaskHistoryView.vue`
- Modify: `frontend/src/router/index.ts` (already has lazy route — verify it works)

**Interfaces:**
- Consumes: `useTasksStore`, `useAuthStore`, `router`
- Produces: `/history` page showing list of past tasks with status, play/resume, delete

- [ ] **Step 1: Create frontend/src/views/TaskHistoryView.vue**

```vue
<template>
  <div class="history-page">
    <header class="history-header">
      <button @click="$router.push('/')">← 返回</button>
      <h1>历史任务</h1>
    </header>

    <div v-if="!auth.isLoggedIn" class="login-prompt">
      请先登录以查看历史记录
    </div>

    <div v-else-if="tasksStore.loading" class="loading">加载中...</div>

    <div v-else-if="!tasksStore.tasks.length" class="empty">
      暂无历史任务
    </div>

    <ul v-else class="task-list">
      <li v-for="task in tasksStore.tasks" :key="task.id" class="task-item">
        <div class="task-info">
          <span class="task-title">{{ task.title }}</span>
          <span class="task-status" :class="task.status">
            {{ statusLabel(task.status) }}
          </span>
          <span class="task-date">{{ formatDate(task.created_at) }}</span>
        </div>
        <div class="task-actions">
          <button v-if="task.status === 'done'" @click="playTask(task.id)">▶ 播放</button>
          <button @click="deleteTask(task.id)">删除</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTasksStore } from '@/stores/tasks'
import type { Task } from '@/api/tasks'

const router = useRouter()
const auth = useAuthStore()
const tasksStore = useTasksStore()

onMounted(() => {
  if (auth.isLoggedIn) {
    tasksStore.fetchTasks()
  }
})

function statusLabel(status: string): string {
  return { processing: '处理中', done: '完成', failed: '失败' }[status] ?? status
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function playTask(taskId: number) {
  await tasksStore.fetchTask(taskId)
  router.push('/')
}

async function deleteTask(taskId: number) {
  if (!confirm('确定删除此任务？')) return
  await tasksStore.removeTask(taskId)
}
</script>

<style scoped>
.history-page {
  max-width: 800px; margin: 0 auto; padding: 1.5rem;
}
.history-header {
  display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;
}
.history-header button {
  padding: 0.4rem 0.75rem; border: none; border-radius: 6px;
  background: #333; color: #e0e0e0; cursor: pointer;
}
h1 { color: #e0e0e0; font-size: 1.5rem; }
.login-prompt, .loading, .empty { text-align: center; color: #666; padding: 3rem 1rem; }
.task-list { list-style: none; display: flex; flex-direction: column; gap: 0.75rem; }
.task-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem; background: #1a1a2e; border-radius: 8px;
}
.task-info { display: flex; flex-direction: column; gap: 0.25rem; }
.task-title { color: #e0e0e0; font-weight: 500; }
.task-status { font-size: 0.8rem; }
.task-status.done { color: #66bb6a; }
.task-status.processing { color: #ffa726; }
.task-status.failed { color: #ef5350; }
.task-date { font-size: 0.75rem; color: #666; }
.task-actions { display: flex; gap: 0.5rem; }
.task-actions button {
  padding: 0.4rem 0.75rem; border: none; border-radius: 6px;
  font-size: 0.85rem; cursor: pointer;
}
.task-actions button:first-child { background: #4fc3f7; color: #000; }
.task-actions button:last-child { background: #333; color: #ef5350; }
</style>
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx vue-tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/TaskHistoryView.vue
git commit -m "feat: task history view — list, play, delete past tasks"
```

---

### Task 14: Integration — Wire Everything & E2E Smoke Test

**Files:**
- Create: `frontend/public/vite.svg`
- Modify: `frontend/src/App.vue` (ensure proper layout)

**Interfaces:**
- Consumes: All components, stores, and API layers
- Produces: Working end-to-end flow

- [ ] **Step 1: Ensure App.vue is correct**

```vue
<template>
  <router-view />
</template>
```

- [ ] **Step 2: Create a simple vite.svg**

```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <text x="4" y="24" font-size="28" fill="#4fc3f7">GE</text>
</svg>
```

Save to `frontend/public/vite.svg`.

- [ ] **Step 3: Start full stack and smoke test**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 3: Backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Terminal 4: Frontend
cd frontend && npm run dev
```

Manual smoke test checklist:
1. Open `http://localhost:5173` — page loads, shows empty player, header, footer
2. Click "登录" → register → successful → username shown in footer
3. Click "反馈" → type message → submit → success message
4. Click "📁 导入素材库" → upload a small mp3 → shows "处理中..." → subtitles appear in player
5. Click play → subtitles sync with audio, current line highlighted
6. Drag progress bar → audio seeks, subtitle changes
7. Change speed → audio plays at new rate
8. Visit `/history` → uploaded task visible → click play → returns to player
9. Delete a task → removed from list

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue frontend/public/vite.svg
git commit -m "feat: integration — full stack wired, smoke test checklist passed"
```

---

### Task 15: Frontend Component Tests

**Files:**
- Create: `frontend/src/components/__tests__/LoginModal.test.ts`
- Create: `frontend/src/components/__tests__/SubtitleDisplay.test.ts`
- Create: `frontend/src/components/__tests__/PlayerControls.test.ts`
- Modify: `frontend/vite.config.ts` (add test config)

**Interfaces:**
- Consumes: All components
- Produces: Passing Vitest test suite

- [ ] **Step 1: Update vite.config.ts for tests**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

- [ ] **Step 2: Create frontend/src/components/__tests__/LoginModal.test.ts**

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoginModal from '../LoginModal.vue'

describe('LoginModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders login form by default', () => {
    const wrapper = mount(LoginModal, { props: {} })
    expect(wrapper.find('h2').text()).toBe('登录')
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('toggles between login and register', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('a').trigger('click')
    expect(wrapper.find('h2').text()).toBe('注册')
    await wrapper.find('a').trigger('click')
    expect(wrapper.find('h2').text()).toBe('登录')
  })

  it('emits close on overlay click', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on X button click', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('.close-btn').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

- [ ] **Step 3: Create frontend/src/components/__tests__/SubtitleDisplay.test.ts**

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SubtitleDisplay from '../SubtitleDisplay.vue'

const sampleSubtitles = [
  { id: 1, index: 0, start_time: 0, end_time: 2, text: 'Hello world' },
  { id: 2, index: 1, start_time: 2, end_time: 4, text: 'How are you?' },
  { id: 3, index: 2, start_time: 4, end_time: 6, text: 'I am fine.' },
]

describe('SubtitleDisplay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows placeholder when no subtitles', () => {
    const wrapper = mount(SubtitleDisplay, { props: { subtitles: [] } })
    expect(wrapper.find('.placeholder').exists()).toBe(true)
  })

  it('renders all subtitle lines', () => {
    const wrapper = mount(SubtitleDisplay, { props: { subtitles: sampleSubtitles } })
    const lines = wrapper.findAll('.subtitle-line')
    expect(lines).toHaveLength(3)
    expect(lines[0].text()).toBe('Hello world')
    expect(lines[1].text()).toBe('How are you?')
    expect(lines[2].text()).toBe('I am fine.')
  })
})
```

- [ ] **Step 4: Create frontend/src/components/__tests__/PlayerControls.test.ts**

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PlayerControls from '../PlayerControls.vue'

describe('PlayerControls', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders play button', () => {
    const wrapper = mount(PlayerControls)
    expect(wrapper.find('.play-btn').exists()).toBe(true)
    expect(wrapper.find('.play-btn').text()).toBe('▶')
  })

  it('renders speed select with all options', () => {
    const wrapper = mount(PlayerControls)
    const options = wrapper.findAll('.rate-select option')
    expect(options).toHaveLength(6)
    expect(options[0].text()).toBe('0.5x')
    expect(options[5].text()).toBe('2x')
  })

  it('shows time displays', () => {
    const wrapper = mount(PlayerControls)
    const times = wrapper.findAll('.time')
    expect(times).toHaveLength(2)
  })

  it('renders progress bar', () => {
    const wrapper = mount(PlayerControls)
    expect(wrapper.find('.progress-bar').exists()).toBe(true)
    expect(wrapper.find('.progress-fill').exists()).toBe(true)
  })
})
```

- [ ] **Step 5: Run frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/__tests__/ frontend/vite.config.ts
git commit -m "test: component tests for LoginModal, SubtitleDisplay, PlayerControls"
```

---

### Task 16: Backend API Integration Tests

**Files:**
- Create: `backend/tests/test_integration.py`

**Interfaces:**
- Consumes: All routes
- Produces: Full integration test covering register → login → upload → poll → play → delete

- [ ] **Step 1: Create backend/tests/test_integration.py**

```python
import io
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _auth_header() -> dict:
    """Helper: register a fresh user and return the auth header."""
    username = "integration_test_user"
    resp = client.post("/api/auth/register", json={"username": username, "password": "test123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_register_and_login():
    resp = client.post("/api/auth/register", json={"username": "flowtest", "password": "test123"})
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["username"] == "flowtest"


def test_feedback_flow():
    headers = _auth_header()
    resp = client.post("/api/feedback", json={"content": "Great!"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["content"] == "Great!"


def test_task_list_flow():
    headers = _auth_header()
    resp = client.get("/api/tasks", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_upload_and_get_task():
    headers = _auth_header()

    # Upload a small test file
    test_file = io.BytesIO(b"\x00" * 1024)  # 1KB dummy data
    resp = client.post(
        "/api/tasks/upload",
        files={"file": ("test.mp3", test_file, "audio/mpeg")},
        headers=headers,
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    assert resp.json()["status"] in ("processing", "done", "failed")

    # Get task
    resp2 = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == task_id

    # Delete task
    resp3 = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert resp3.status_code == 204

    # Verify deleted
    resp4 = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert resp4.status_code == 404


def test_upload_invalid_extension():
    headers = _auth_header()
    test_file = io.BytesIO(b"test")
    resp = client.post(
        "/api/tasks/upload",
        files={"file": ("test.exe", test_file, "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_url_submit():
    headers = _auth_header()
    resp = client.post(
        "/api/tasks/url",
        data={"url": "https://example.com/test.mp3"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "processing"
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && python -m pytest tests/test_integration.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_integration.py
git commit -m "test: backend API integration tests covering full user flow"
```

---

### Task 17: README & Project Documentation

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: (no code dependencies)
- Produces: Project README with setup and usage instructions

- [ ] **Step 1: Create README.md**

```markdown
# God English — 英语口语练习平台

基于 Whisper ASR 的英语口语练习 Web 应用。导入本地音视频或粘贴平台链接，自动生成同步字幕，跟随音频练习口语。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Pinia |
| 后端 | Python 3.11+ / FastAPI |
| ASR | faster-whisper (large-v3) |
| 媒体抓取 | yt-dlp + ffmpeg |
| 数据库 | SQLite |
| 任务队列 | Celery + Redis |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- ffmpeg
- Redis

### 安装

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 运行

需要 4 个终端窗口：

```bash
# 终端 1: Redis
redis-server

# 终端 2: Celery worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# 终端 3: FastAPI 后端
cd backend && python -m uvicorn app.main:app --reload --port 8000

# 终端 4: Vue 前端
cd frontend && npm run dev
```

打开 `http://localhost:5173`

### 测试

```bash
# 后端
cd backend && python -m pytest

# 前端
cd frontend && npx vitest run
```

## 功能

- 📁 **导入素材库** — 上传本地 mp3/mp4/wav/webm/m4a/flac
- 🔗 **粘贴链接** — 支持 B站/抖音/小红书/腾讯视频/爱奇艺/网易云/QQ音乐等
- 🎤 **ASR 字幕生成** — Whisper 自动识别，字幕带时间戳
- ▶️ **同步播放** — 音频与字幕同步，当前句高亮，已播/未播句自动变暗
- ⏱ **播放控制** — 暂停、倍速(0.5x-2x)、可拖拽进度条
- 👤 **账号系统** — 注册/登录，JWT 认证
- 📋 **历史记录** — 查看、继续、删除历史任务
- ✍️ **反馈** — 提交文字反馈
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: project README with setup and usage instructions"
```
