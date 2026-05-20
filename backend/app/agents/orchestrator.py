from __future__ import annotations

import json

from ..models.session import SessionPhase, StudentSession
from ..tutor_brain.curriculum import list_chapters


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
            return int(raw_grade)
        except (TypeError, ValueError):
            return fallback

    def _normalize_chapter_key(self, value: object) -> str:
        return " ".join(str(value or "").replace("_", " ").replace("-", " ").lower().split())

    def _select_chapter_index(self, chapters: list[dict], preferred_chapter: object = None) -> int:
        preferred = self._normalize_chapter_key(preferred_chapter)
        if not preferred:
            return 0

        for index, chapter in enumerate(chapters):
            if not isinstance(chapter, dict):
                continue
            candidates = [
                chapter.get("slug"),
                chapter.get("title"),
                chapter.get("chapter"),
                chapter.get("name"),
            ]
            for candidate in candidates:
                normalized = self._normalize_chapter_key(candidate)
                if not normalized:
                    continue
                if preferred == normalized or preferred in normalized or normalized in preferred:
                    return index
        return 0

    def _initialize_grade_curriculum(self, session: StudentSession, grade: int, preferred_chapter: object = None) -> None:
        session.grade = grade
        exam = getattr(session, "exam", "cbse")
        chapters = list_chapters(grade, exam)
        session.topic_problem_cursors = {}
        session.topic_problem_history = {}
        session.topic_problem_quotas = {}

        if not chapters:
            session.current_chapter_index = 0
            session.chapter_name = "Welcome"
            session.agenda = ["Introduction"]
            session.current_topic_index = 0
            session.current_topic = "Introduction"
            return

        chapter_index = self._select_chapter_index(chapters, preferred_chapter)
        selected_chapter = chapters[chapter_index]
        session.current_chapter_index = chapter_index
        session.chapter_name = selected_chapter.get("title") or selected_chapter.get("chapter") or f"Chapter {chapter_index + 1}"
        agenda = self._chapter_agenda(selected_chapter, fallback=session.chapter_name)

        session.agenda = agenda if agenda else [session.chapter_name]
        session.current_topic_index = 0
        session.current_topic = session.agenda[0]
        session.chapter_transition = None

    def _chapter_agenda(self, chapter: dict, *, fallback: str) -> list[str]:
        agenda: list[str] = []
        if isinstance(chapter.get("agenda"), list):
            agenda = [str(item).strip() for item in chapter["agenda"] if str(item).strip()]
        elif isinstance(chapter.get("book_topics"), list):
            agenda = [str(item).strip() for item in chapter["book_topics"] if str(item).strip()]
        elif isinstance(chapter.get("concepts"), list):
            agenda = [
                str(item.get("title", "")).strip()
                for item in chapter["concepts"]
                if isinstance(item, dict) and str(item.get("title", "")).strip()
            ]
        return agenda if agenda else [fallback]

    def _advance_to_next_topic(self, session: StudentSession) -> str:
        if not session.agenda:
            self._initialize_grade_curriculum(session, getattr(session, "grade", 10))

        previous_chapter = session.chapter_name
        chapter_changed = False
        session.current_topic_index += 1

        if session.current_topic_index >= len(session.agenda):
            exam = getattr(session, "exam", "cbse")
            grade = getattr(session, "grade", 10)
            chapters = list_chapters(grade, exam)
            next_chapter_index = session.current_chapter_index + 1

            if next_chapter_index < len(chapters):
                next_chapter = chapters[next_chapter_index]
                session.current_chapter_index = next_chapter_index
                session.chapter_name = (
                    next_chapter.get("title")
                    or next_chapter.get("chapter")
                    or f"Chapter {next_chapter_index + 1}"
                )
                chapter_changed = True
                agenda = self._chapter_agenda(next_chapter, fallback=session.chapter_name)

                session.agenda = agenda if agenda else [session.chapter_name]
                session.current_topic_index = 0
            else:
                session.current_topic_index = max(0, len(session.agenda) - 1)

        next_topic = (
            session.agenda[session.current_topic_index]
            if session.agenda and 0 <= session.current_topic_index < len(session.agenda)
            else session.chapter_name
        )
        session.current_topic = next_topic
        if chapter_changed:
            session.chapter_transition = {
                "from_chapter": previous_chapter,
                "to_chapter": session.chapter_name,
                "topics": list(session.agenda or []),
                "first_topic": next_topic,
            }
            session.next_system_note = (
                "SYSTEM NOTE: Previous chapter is complete. Announce chapter completion and then start the new chapter. "
                f"New chapter: {session.chapter_name}. Begin with topic: {next_topic}. "
                "Also introduce the chapter topic list clearly."
            )
        else:
            session.chapter_transition = None
            session.next_system_note = (
                "SYSTEM NOTE: The student pressed Next. You MUST move on to the next topic on the agenda: "
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

        session.exam = "jee" if exam == "jee" else "cbse"
        grade = self._normalize_grade(context, getattr(session, "grade", 10))
        preferred_chapter = (context or {}).get("chapter") or (context or {}).get("chapter_slug")

        action = ""
        if message_text.startswith("{") and message_text.endswith("}"):
            try:
                payload = json.loads(message_text)
                if isinstance(payload, dict):
                    action = str(payload.get("action", "")).strip().lower()
            except json.JSONDecodeError:
                action = ""
            if action in {"skip_topic", "skip_chapter", "next_chapter"}:
                action = "next_topic"
            elif action == "next":
                action = "next_step"
        elif message in {"next topic", "next_topic", "next chapter", "next_chapter", "skip topic", "skip_topic", "skip chapter", "skip_chapter", "skip ahead"}:
            action = "next_topic"
        elif message in {"next", "next_step"}:
            action = "next_step"
        elif message in {"start", "begin"}:
            action = "start"
        elif len(message) < 25 and any(
            phrase in message
            for phrase in ["understood", "got it", "makes sense", "move on", "go ahead", "clear"]
        ):
            action = "next_step"

        if action == "start":
            self._initialize_grade_curriculum(session, grade, preferred_chapter)
            session.is_first_interaction = True
            session.next_system_note = None
            session.questions_asked = 0
            session.class_problem_cursor = 0
        elif mode_normalized == "class" and action == "next_topic":
            self._advance_to_next_topic(session)
        elif mode_normalized == "class" and action == "next_step":
            session.next_system_note = (
                "SYSTEM NOTE: The student pressed Next for the same topic. "
                "Continue from the current step in this topic. "
                "Do not restart the chapter introduction and do not repeat the same solved example."
            )
        elif not session.agenda or session.current_topic is None:
            self._initialize_grade_curriculum(session, grade)

        if session.exam == "jee" and mode_normalized in {"mock_test", "exam"}:
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
