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
