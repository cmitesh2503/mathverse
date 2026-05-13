from __future__ import annotations

import json

from ..models.session import SessionPhase, StudentSession
from ..tutor_brain.curriculum import get_jee_chapter_plan, get_jee_classroom_flow


class Orchestrator:
    ANSWER_KEYWORDS = ("answer is", "submitted", "final")
    HELP_KEYWORDS = ("hint", "help", "stuck")

    def __init__(self) -> None:
        self.sessions: dict[str, StudentSession] = {}
        self.active_sessions = self.sessions

    def get_or_create_session(self, session_id: str) -> StudentSession:
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = StudentSession(session_id=session_id)
        return self.active_sessions[session_id]

    def _normalize_grade(self, context: dict | None, fallback: int) -> int:
        raw_grade = (context or {}).get("grade", fallback)
        try:
            parsed = int(raw_grade)
        except (TypeError, ValueError):
            return fallback
        return 12 if parsed == 12 else 11

    def _initialize_grade_curriculum(self, session: StudentSession, grade: int) -> None:
        chapter_plan = get_jee_chapter_plan(grade, 0)
        session.grade = grade
        session.current_chapter_index = int(chapter_plan["chapter_index"])
        session.chapter_name = str(chapter_plan["chapter"])
        session.agenda = [str(topic) for topic in chapter_plan["agenda"]]
        session.current_topic_index = 0
        session.current_topic = session.agenda[0] if session.agenda else session.chapter_name

    def _advance_to_next_topic(self, session: StudentSession) -> str:
        if not session.agenda:
            self._initialize_grade_curriculum(session, getattr(session, "grade", 11))

        session.current_topic_index += 1
        if session.current_topic_index >= len(session.agenda):
            next_chapter_index = session.current_chapter_index + 1
            chapter_flow = get_jee_classroom_flow(getattr(session, "grade", 11))
            if next_chapter_index < len(chapter_flow):
                next_plan = get_jee_chapter_plan(session.grade, next_chapter_index)
                session.current_chapter_index = int(next_plan["chapter_index"])
                session.chapter_name = str(next_plan["chapter"])
                session.agenda = [str(topic) for topic in next_plan["agenda"]]
                session.current_topic_index = 0
            else:
                session.current_topic_index = max(0, len(session.agenda) - 1)

        next_topic = (
            session.agenda[session.current_topic_index]
            if session.agenda and 0 <= session.current_topic_index < len(session.agenda)
            else session.chapter_name
        )
        session.current_topic = next_topic
        session.next_system_note = (
            "SYSTEM NOTE: The student pressed 'Next'. You MUST move on to the next topic on the agenda: "
            f"{next_topic}."
        )
        return next_topic

    async def route_message(
        self,
        session_id: str,
        user_message: str,
        *,
        mode: str | None = None,
        context: dict | None = None,
    ) -> str:
        session = self.get_or_create_session(session_id)
        phase = session.active_phase
        message_text = str(user_message or "").strip()
        message = message_text.lower()
        exam = str((context or {}).get("exam", "")).lower()
        mode_normalized = (mode or "").lower()
        grade = self._normalize_grade(context, getattr(session, "grade", 11))
        session.exam = "jee" if exam == "jee" else "cbse"

        action = ""
        if message_text.startswith("{") and message_text.endswith("}"):
            try:
                payload = json.loads(message_text)
                if isinstance(payload, dict):
                    action = str(payload.get("action", "")).strip().lower()
            except json.JSONDecodeError:
                action = ""
        elif message in {"next", "next_step", "next topic", "next_topic"}:
            action = "next"
        elif message in {"start", "begin"}:
            action = "start"

        if action == "start":
            self._initialize_grade_curriculum(session, grade)
        elif mode_normalized == "class" and action == "next":
            self._advance_to_next_topic(session)
        elif not session.agenda or session.current_topic is None:
            self._initialize_grade_curriculum(session, grade)

        if exam == "jee" and mode_normalized in {"mock_test", "exam"}:
            return "proctor_agent"

        if phase == SessionPhase.TEACHING:
            return "tutor_agent"

        if phase == SessionPhase.TESTING:
            return "proctor_agent"

        if phase == SessionPhase.PRACTICE:
            if any(keyword in message for keyword in self.ANSWER_KEYWORDS):
                return "diagnostic_agent"

            if any(keyword in message for keyword in self.HELP_KEYWORDS):
                return "tutor_agent"

        return "tutor_agent"
