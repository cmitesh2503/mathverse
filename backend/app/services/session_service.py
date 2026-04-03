from __future__ import annotations

import json
import uuid
from datetime import timezone
from pathlib import Path
from threading import Lock

from ..models.session import (
    LessonSnapshot,
    SessionOverview,
    StartSessionRequest,
    StudentProfile,
    TranscriptTurn,
    TutorSessionRecord,
    utc_now,
)
from ..tutor_brain.curriculum import get_default_topic_slug, get_topic


STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "class_sessions.json"


class SessionService:
    def __init__(self, store_path: Path = STORE_PATH):
        self.store_path = store_path
        self._lock = Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def _empty_store(self) -> dict:
        return {"sessions": {}, "students": {}}

    def _load_store(self) -> dict:
        if not self.store_path.exists():
            return self._empty_store()

        raw = self.store_path.read_text(encoding="utf-8").strip()
        if not raw:
            return self._empty_store()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._empty_store()

        data.setdefault("sessions", {})
        data.setdefault("students", {})
        return data

    def _save_store(self, store: dict) -> None:
        self.store_path.write_text(
            json.dumps(store, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _serialize(self, model) -> dict:
        return json.loads(model.model_dump_json())

    def _overview(self, session: TutorSessionRecord) -> SessionOverview:
        return SessionOverview(
            session_id=session.session_id,
            title=session.title,
            grade=session.grade,
            topic_title=session.topic_title,
            lesson_stage=session.lesson_stage,
            summary=session.summary,
            updated_at=session.updated_at,
        )

    def _build_title(self, grade: int, topic_title: str | None) -> str:
        stamp = utc_now().astimezone(timezone.utc).strftime("%d %b %Y")
        label = topic_title or "CBSE Math"
        return f"Class {grade} - {label} - {stamp}"

    def _ensure_profile(self, store: dict, request: StartSessionRequest) -> StudentProfile:
        existing = store["students"].get(request.student_id)
        if existing:
            profile = StudentProfile.model_validate(existing)
        else:
            profile = StudentProfile(
                student_id=request.student_id,
                board=request.board,
                subject=request.subject,
            )

        if request.grade not in profile.grades_seen:
            profile.grades_seen.append(request.grade)

        profile.board = request.board
        profile.subject = request.subject
        profile.last_active_at = utc_now()
        store["students"][request.student_id] = self._serialize(profile)
        return profile

    def _latest_session_id(self, store: dict, student_id: str, grade: int) -> str | None:
        profile_raw = store["students"].get(student_id)
        if not profile_raw:
            return None

        profile = StudentProfile.model_validate(profile_raw)
        candidates: list[TutorSessionRecord] = []
        for session_id in profile.session_ids:
            session_raw = store["sessions"].get(session_id)
            if not session_raw:
                continue

            session = TutorSessionRecord.model_validate(session_raw)
            if session.grade == grade:
                candidates.append(session)

        if not candidates:
            return None

        candidates.sort(key=lambda record: record.updated_at, reverse=True)
        return candidates[0].session_id

    def _sessions_for_student(
        self,
        store: dict,
        student_id: str,
        grade: int | None = None,
        exclude_session_id: str | None = None,
    ) -> list[TutorSessionRecord]:
        profile_raw = store["students"].get(student_id)
        if not profile_raw:
            return []

        profile = StudentProfile.model_validate(profile_raw)
        sessions: list[TutorSessionRecord] = []
        for session_id in profile.session_ids:
            if exclude_session_id and session_id == exclude_session_id:
                continue

            session_raw = store["sessions"].get(session_id)
            if not session_raw:
                continue

            session = TutorSessionRecord.model_validate(session_raw)
            if grade is None or session.grade == grade:
                sessions.append(session)

        sessions.sort(key=lambda record: record.updated_at, reverse=True)
        return sessions

    def create_or_resume_session(self, request: StartSessionRequest) -> TutorSessionRecord:
        with self._lock:
            store = self._load_store()
            profile = self._ensure_profile(store, request)

            session_id = request.session_id
            if not request.start_new and not session_id:
                session_id = self._latest_session_id(store, request.student_id, request.grade)

            if session_id and session_id in store["sessions"]:
                session = TutorSessionRecord.model_validate(store["sessions"][session_id])
                session.grade = request.grade
                session.board = request.board
                session.subject = request.subject
                session.updated_at = utc_now()
            else:
                topic_slug = request.topic_slug or get_default_topic_slug(request.grade)
                topic = get_topic(request.grade, topic_slug)
                topic_title = topic["title"] if topic else None
                session = TutorSessionRecord(
                    session_id=session_id or str(uuid.uuid4()),
                    student_id=request.student_id,
                    grade=request.grade,
                    board=request.board,
                    subject=request.subject,
                    topic_slug=topic_slug,
                    topic_title=topic_title,
                    title=self._build_title(request.grade, topic_title),
                    summary=f"{topic_title or 'Math lesson'} is ready to begin.",
                )

            if session.session_id in profile.session_ids:
                profile.session_ids = [
                    current for current in profile.session_ids if current != session.session_id
                ]
            profile.session_ids.insert(0, session.session_id)

            if session.topic_title:
                recent_topics = [topic for topic in profile.recent_topics if topic != session.topic_title]
                recent_topics.insert(0, session.topic_title)
                profile.recent_topics = recent_topics[:8]

            profile.last_active_at = utc_now()

            store["sessions"][session.session_id] = self._serialize(session)
            store["students"][profile.student_id] = self._serialize(profile)
            self._save_store(store)
            return session

    def get_session(self, session_id: str) -> TutorSessionRecord | None:
        with self._lock:
            store = self._load_store()
            raw = store["sessions"].get(session_id)
            if not raw:
                return None
            return TutorSessionRecord.model_validate(raw)

    def list_sessions(self, student_id: str, grade: int | None = None) -> list[dict]:
        with self._lock:
            store = self._load_store()
            profile_raw = store["students"].get(student_id)
            if not profile_raw:
                return []

            profile = StudentProfile.model_validate(profile_raw)
            sessions: list[SessionOverview] = []
            for session_id in profile.session_ids:
                raw = store["sessions"].get(session_id)
                if not raw:
                    continue
                session = TutorSessionRecord.model_validate(raw)
                if grade is None or session.grade == grade:
                    sessions.append(self._overview(session))

            sessions.sort(key=lambda item: item.updated_at, reverse=True)
            return [self._serialize(item) for item in sessions]

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        transport: str = "text",
    ) -> TutorSessionRecord | None:
        with self._lock:
            store = self._load_store()
            raw = store["sessions"].get(session_id)
            if not raw:
                return None

            session = TutorSessionRecord.model_validate(raw)
            session.transcript.append(
                TranscriptTurn(role=role, content=content, transport=transport)
            )
            session.updated_at = utc_now()
            session.summary = self._auto_summary(session)
            store["sessions"][session_id] = self._serialize(session)
            self._save_store(store)
            return session

    def update_lesson_snapshot(
        self,
        session_id: str,
        snapshot: LessonSnapshot,
    ) -> TutorSessionRecord | None:
        with self._lock:
            store = self._load_store()
            raw = store["sessions"].get(session_id)
            if not raw:
                return None

            session = TutorSessionRecord.model_validate(raw)
            session.lesson_stage = snapshot.stage
            session.topic_slug = snapshot.topic_slug or session.topic_slug
            session.topic_title = snapshot.topic_title or session.topic_title
            if snapshot.summary:
                session.summary = snapshot.summary
            if snapshot.note_cards:
                session.lesson_notes = snapshot.note_cards[:6]
            session.metadata.update(
                {
                    "concept_id": snapshot.concept_id,
                    "concept_title": snapshot.concept_title,
                    "whiteboard": snapshot.whiteboard,
                }
            )
            session.updated_at = utc_now()
            store["sessions"][session_id] = self._serialize(session)
            self._save_store(store)
            return session

    def update_session_metadata(
        self,
        session_id: str,
        metadata_updates: dict,
    ) -> TutorSessionRecord | None:
        with self._lock:
            store = self._load_store()
            raw = store["sessions"].get(session_id)
            if not raw:
                return None

            session = TutorSessionRecord.model_validate(raw)
            session.metadata.update(metadata_updates)
            session.updated_at = utc_now()
            store["sessions"][session_id] = self._serialize(session)
            self._save_store(store)
            return session

    def serialize_session(self, session: TutorSessionRecord, include_transcript: bool = False) -> dict:
        payload = {
            "session_id": session.session_id,
            "student_id": session.student_id,
            "title": session.title,
            "board": session.board,
            "subject": session.subject,
            "grade": session.grade,
            "topic_slug": session.topic_slug,
            "topic_title": session.topic_title,
            "tutor_name": session.tutor_name,
            "lesson_stage": session.lesson_stage,
            "summary": session.summary,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "lesson_notes": session.lesson_notes,
            "metadata": session.metadata,
        }
        if include_transcript:
            payload["transcript"] = [self._serialize(turn) for turn in session.transcript]
        return payload

    def build_memory_context(self, session_id: str) -> str:
        with self._lock:
            store = self._load_store()
            raw = store["sessions"].get(session_id)
            if not raw:
                return ""

            session = TutorSessionRecord.model_validate(raw)
            recent_turns = session.transcript[-6:]
            history = "\n".join(
                f"{turn.role.title()}: {turn.content}" for turn in recent_turns if turn.content
            )

            notes = "\n".join(f"- {note}" for note in session.lesson_notes[:4])
            topic_label = session.topic_title or "current topic"
            previous_sessions = self._sessions_for_student(
                store,
                session.student_id,
                session.grade,
                exclude_session_id=session.session_id,
            )[:3]

            previous_memory = "\n".join(
                (
                    f"- {item.topic_title or 'Math lesson'}: "
                    f"{item.summary or 'Class history available.'}"
                )
                for item in previous_sessions
            )

            return (
                f"Student is in CBSE class {session.grade} mathematics.\n"
                f"Current lesson: {topic_label}\n"
                f"Lesson stage: {session.lesson_stage}\n"
                f"Session summary: {session.summary}\n"
                f"Key notes:\n{notes or '- No notes yet.'}\n"
                f"Recent conversation:\n{history or 'No prior conversation yet.'}\n"
                f"Memory from earlier saved classes:\n"
                f"{previous_memory or '- No earlier saved classes yet.'}"
            )

    def _auto_summary(self, session: TutorSessionRecord) -> str:
        topic_label = session.topic_title or "Math lesson"
        last_user = next(
            (turn.content for turn in reversed(session.transcript) if turn.role == "user"),
            "",
        )
        if not last_user:
            return session.summary or f"{topic_label} is ready to begin."
        preview = last_user.strip().replace("\n", " ")
        preview = preview[:100] + ("..." if len(preview) > 100 else "")
        return f"{topic_label}: recently discussed '{preview}'."


session_service = SessionService()
