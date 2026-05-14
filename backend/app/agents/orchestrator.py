from __future__ import annotations
import json
from ..models.session import SessionPhase, StudentSession

# ✅ Use the new dynamic Firestore loader instead of hardcoded JEE functions
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
            return int(raw_grade) # ✅ Stop forcing Grade 11! Respect the actual grade.
        except (TypeError, ValueError):
            return fallback

    def _initialize_grade_curriculum(self, session: StudentSession, grade: int) -> None:
        session.grade = grade
        exam = getattr(session, "exam", "cbse")
        
        # ✅ Fetch the correct syllabus directly from Firestore
        chapters = list_chapters(grade, exam)

        if not chapters:
            session.current_chapter_index = 0
            session.chapter_name = "Welcome"
            session.agenda = ["Introduction"]
            session.current_topic_index = 0
            session.current_topic = "Introduction"
            return

        first_chapter = chapters[0]
        session.current_chapter_index = 0
        
        # Handle both CBSE ("title") and JEE ("chapter") formats
        session.chapter_name = first_chapter.get("title") or first_chapter.get("chapter") or "Chapter 1"

        agenda = []
        if "agenda" in first_chapter:
            agenda = [str(a) for a in first_chapter["agenda"]]
        elif "concepts" in first_chapter:
            agenda = [str(c.get("title", "")) for c in first_chapter["concepts"]]

        session.agenda = agenda if agenda else [session.chapter_name]
        session.current_topic_index = 0
        session.current_topic = session.agenda[0]

    def _advance_to_next_topic(self, session: StudentSession) -> str:
        if not session.agenda:
            self._initialize_grade_curriculum(session, getattr(session, "grade", 10))

        session.current_topic_index += 1
        
        if session.current_topic_index >= len(session.agenda):
            exam = getattr(session, "exam", "cbse")
            grade = getattr(session, "grade", 10)
            chapters = list_chapters(grade, exam)
            next_chapter_index = session.current_chapter_index + 1
            
            if next_chapter_index < len(chapters):
                next_chapter = chapters[next_chapter_index]
                session.current_chapter_index = next_chapter_index
                session.chapter_name = next_chapter.get("title") or next_chapter.get("chapter") or f"Chapter {next_chapter_index + 1}"
                
                agenda = []
                if "agenda" in next_chapter:
                    agenda = [str(a) for a in next_chapter["agenda"]]
                elif "concepts" in next_chapter:
                    agenda = [str(c.get("title", "")) for c in next_chapter["concepts"]]

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
        
        # ✅ Ensure Exam and Grade respect the frontend
        session.exam = "jee" if exam == "jee" else "cbse"
        grade = self._normalize_grade(context, getattr(session, "grade", 10))

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
        # ✅ NEW: Allow natural voice affirmations to trigger progression
        elif len(message) < 25 and any(phrase in message for phrase in ["understood", "got it", "makes sense", "move on", "continue", "go ahead", "clear"]):
            action = "next"

        if action == "start":
            self._initialize_grade_curriculum(session, grade)
        elif mode_normalized == "class" and action == "next":
            self._advance_to_next_topic(session)
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