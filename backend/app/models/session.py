from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptTurn(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    transport: Literal["text", "audio", "bidi"] = "text"
    timestamp: datetime = Field(default_factory=utc_now)


class LessonSnapshot(BaseModel):
    stage: str = "INTRO"
    topic_slug: str | None = None
    topic_title: str | None = None
    concept_id: str | None = None
    concept_title: str | None = None
    summary: str = ""
    note_cards: list[str] = Field(default_factory=list)
    whiteboard: dict[str, Any] = Field(default_factory=dict)


class TutorSessionRecord(BaseModel):
    session_id: str
    student_id: str
    title: str
    board: str = "CBSE"
    subject: str = "Mathematics"
    grade: int
    topic_slug: str | None = None
    topic_title: str | None = None
    tutor_name: str = "Ava"
    lesson_stage: str = "INTRO"
    summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    lesson_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudentProfile(BaseModel):
    student_id: str
    display_name: str = "Learner"
    board: str = "CBSE"
    subject: str = "Mathematics"
    grades_seen: list[int] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    watch_fors: list[str] = Field(default_factory=list)
    last_active_at: datetime = Field(default_factory=utc_now)


class StartSessionRequest(BaseModel):
    student_id: str = "local-student"
    grade: int = 10
    board: str = "CBSE"
    subject: str = "Mathematics"
    session_id: str | None = None
    topic_slug: str | None = None
    start_new: bool = False


class SessionMessageRequest(BaseModel):
    session_id: str
    message: str


class SessionOverview(BaseModel):
    session_id: str
    title: str
    grade: int
    topic_title: str | None = None
    lesson_stage: str
    summary: str
    updated_at: datetime
