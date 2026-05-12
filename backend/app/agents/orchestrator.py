from __future__ import annotations

from ..models.session import SessionPhase, StudentSession


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

    async def route_message(self, session_id: str, user_message: str) -> str:
        session = self.get_or_create_session(session_id)
        phase = session.active_phase
        message = user_message.lower()

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
