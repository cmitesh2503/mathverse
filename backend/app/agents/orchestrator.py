from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from ..models.session import SessionPhase, StudentSession
from ..services.ai_gateway import generate_response
from ..tutor_brain.curriculum import list_chapters


class Orchestrator:
    ANSWER_KEYWORDS = ("answer is", "submitted", "final")
    HELP_KEYWORDS = ("hint", "help", "stuck")
    SESSION_TTL_SECONDS = 24 * 60 * 60
    _memory_sessions: dict[str, tuple[str, float]] = {}

    ORCHESTRATOR_ROUTING_PROMPT = """
You are the Orchestrator for an AI math tutoring system. Your job is to classify the user's latest input and route them to the correct specialist agent.

AVAILABLE AGENTS:
1. "tutor_agent": Handles theory teaching, concept explanations, follow-up doubts ("why?", "how?"), requests for the next topic, and general progression ("next", "continue").
2. "diagnostic_agent": Handles the practice phase. Route here IF the user explicitly asks for questions, exercises, or a test, OR if the user provides an answer to a math problem (e.g., "42", "x=5", "option B").
3. "proctor_agent": Handles completely off-topic chat, inappropriate behavior, or attempts to bypass the system.

CURRENT SESSION CONTEXT:
- Active Phase: {active_phase}
- Current Topic: {current_topic}

USER MESSAGE: "{user_message}"

CRITICAL TRANSITION RULES:
- If Active Phase is "teaching" but the user says "give me a question", "let's practice", "test me", "solve exercise", or inputs what looks like a math answer -> route to "diagnostic_agent" (Transition to Practice).
- If Active Phase is "practice" but the user says "I don't understand", "teach me the theory again", "explain this concept", or "next topic" -> route to "tutor_agent" (Transition to Theory).
- If the user simply says "next", "continue", or "ready", route based on the Active Phase.

Based on the rules above, output ONLY the exact name of the agent to route to ("tutor_agent", "diagnostic_agent", or "proctor_agent"). Do not include any formatting, markdown, or other text.
    """

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis_key_prefix = os.getenv("ORCHESTRATOR_SESSION_KEY_PREFIX", "orchestrator:session:")
        configured_store = os.getenv("ORCHESTRATOR_STORE", "").strip().lower()
        self._require_redis = os.getenv("ORCHESTRATOR_REQUIRE_REDIS", "").lower() in {"1", "true", "yes"}
        self._use_memory_store = (
            not self._require_redis
            and (configured_store == "memory" or (not configured_store and not os.getenv("REDIS_URL")))
        )
        self.redis_client = None
        if not self._use_memory_store:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )

    def _phase_value(self, session: StudentSession) -> str:
        raw_phase = getattr(session, "active_phase", SessionPhase.TEACHING)
        return str(getattr(raw_phase, "value", raw_phase) or SessionPhase.TEACHING.value).strip().lower()

    def _set_active_phase(self, session: StudentSession, phase: SessionPhase) -> None:
        session.active_phase = phase
        session.current_phase = phase.value

    def _redis_key(self, session_id: str) -> str:
        return f"{self._redis_key_prefix}{session_id}"

    def _memory_get(self, session_id: str) -> str | None:
        key = self._redis_key(session_id)
        item = self._memory_sessions.get(key)
        if item is None:
            return None

        serialized, expires_at = item
        if expires_at <= time.monotonic():
            self._memory_sessions.pop(key, None)
            return None
        return serialized

    def _memory_set(self, session_id: str, serialized: str) -> None:
        expires_at = time.monotonic() + self.SESSION_TTL_SECONDS
        self._memory_sessions[self._redis_key(session_id)] = (serialized, expires_at)

    def _fallback_to_memory(self, error: Exception) -> None:
        if self._require_redis:
            raise error
        self._use_memory_store = True

    async def verify_connection(self) -> bool:
        if self._use_memory_store:
            return True
        if self.redis_client is None:
            return True
        try:
            return bool(await asyncio.wait_for(self.redis_client.ping(), timeout=2))
        except (OSError, RedisError, TimeoutError, asyncio.TimeoutError) as error:
            self._fallback_to_memory(error)
            print(f"Redis unavailable; using in-memory orchestrator sessions ({type(error).__name__}: {error})")
            return True

    async def get_session(self, session_id: str) -> StudentSession | None:
        if self._use_memory_store:
            raw = self._memory_get(session_id)
        else:
            try:
                if self.redis_client is None:
                    return None
                raw = await self.redis_client.get(self._redis_key(session_id))
            except (OSError, RedisError) as error:
                self._fallback_to_memory(error)
                raw = self._memory_get(session_id)
        if not raw:
            return None

        payload = json.loads(raw)
        return StudentSession.model_validate(payload)

    async def set_session(self, session_id: str, data: StudentSession | dict[str, Any]) -> StudentSession:
        session = data if isinstance(data, StudentSession) else StudentSession.model_validate(data)
        session.session_id = session_id

        serialized = json.dumps(session.model_dump(mode="json"), ensure_ascii=False)
        if self._use_memory_store:
            self._memory_set(session_id, serialized)
        else:
            try:
                if self.redis_client is None:
                    self._memory_set(session_id, serialized)
                    return session
                await self.redis_client.set(self._redis_key(session_id), serialized, ex=self.SESSION_TTL_SECONDS)
            except (OSError, RedisError) as error:
                self._fallback_to_memory(error)
                self._memory_set(session_id, serialized)
        return session

    async def get_or_create_session(self, session_id: str) -> StudentSession:
        existing = await self.get_session(session_id)
        if existing is not None:
            return existing

        created = StudentSession(
            session_id=session_id,
            active_phase=SessionPhase.TEACHING,
            current_phase=SessionPhase.TEACHING.value,
        )
        await self.set_session(session_id, created)
        return created

    async def start_session(
        self,
        session_id: str,
        *,
        context: dict | None = None,
        session: StudentSession | None = None,
    ) -> StudentSession:
        target = session if session is not None else await self.get_or_create_session(session_id)
        grade = self._normalize_grade(context, getattr(target, "grade", 10))
        preferred_chapter = (context or {}).get("chapter") or (context or {}).get("chapter_slug")
        self._initialize_grade_curriculum(target, grade, preferred_chapter)
        self._set_active_phase(target, SessionPhase.TEACHING)
        target.is_first_interaction = True
        target.next_system_note = None
        target.questions_asked = 0
        target.class_problem_cursor = 0
        target.class_intro_done = False
        target.concept_teaching_index = 0
        target.concept_teaching_complete = False
        target.exercise_phase_started = False
        await self.set_session(session_id, target)
        return target

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
        session.class_intro_done = False
        session.concept_teaching_index = 0
        session.concept_teaching_complete = False
        session.exercise_phase_started = False

        if not chapters:
            session.current_chapter_index = 0
            session.chapter_name = "Welcome"
            session.current_chapter = session.chapter_name
            session.agenda = ["Introduction"]
            session.current_topic_index = 0
            session.current_topic = "Introduction"
            return

        chapter_index = self._select_chapter_index(chapters, preferred_chapter)
        selected_chapter = chapters[chapter_index]
        session.current_chapter_index = chapter_index
        session.chapter_name = selected_chapter.get("title") or selected_chapter.get("chapter") or f"Chapter {chapter_index + 1}"
        session.current_chapter = session.chapter_name
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

    def _reset_chapter_teaching_state(self, session: StudentSession) -> None:
        self._set_active_phase(session, SessionPhase.TEACHING)
        session.class_intro_done = False
        session.concept_teaching_index = 0
        session.concept_teaching_complete = False
        session.exercise_phase_started = False
        session.next_problem_actions = []

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
                session.current_chapter = session.chapter_name
                chapter_changed = True
                agenda = self._chapter_agenda(next_chapter, fallback=session.chapter_name)

                session.agenda = agenda if agenda else [session.chapter_name]
                session.current_topic_index = 0
                self._reset_chapter_teaching_state(session)
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
            self._set_active_phase(session, SessionPhase.TEACHING)
            session.concept_teaching_index = max(0, session.current_topic_index)
            session.concept_teaching_complete = False
            session.exercise_phase_started = False
            session.next_problem_actions = []
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
        session: StudentSession | None = None,
    ) -> str:
        session = session if session is not None else await self.get_or_create_session(session_id)
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
        elif message in {"homework", "finish", "end"}:
            action = "homework"
        elif message in {"next exercise", "next_exercise", "next pdf exercise", "next_pdf_exercise"}:
            action = "next_exercise"
        elif len(message) < 25 and any(
            phrase in message
            for phrase in ["understood", "got it", "makes sense", "move on", "go ahead", "clear"]
        ):
            action = "next_step"

        if action == "start":
            session = await self.start_session(
                session_id,
                context=context,
                session=session,
            )
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

        phase = self._phase_value(session)
        practice_only_actions = {
            "homework",
            "finish",
            "end",
            "next_exercise",
            "next_pdf_exercise",
            "solve_pdf_exercises",
            "solve_all_exercises",
            "solve_all_pdf_exercises",
            "skip_homework",
        }
        if phase == SessionPhase.TEACHING.value and action in practice_only_actions:
            session.next_system_note = (
                "SYSTEM NOTE: Keep this turn in THEORY mode only. "
                "Do not generate homework or practice exercises yet. "
                "Continue the current chapter explanation and concept board work."
            )
            await self.set_session(session_id, session)
            return "tutor_agent"

        if session.exam == "jee" and mode_normalized in {"mock_test", "exam"}:
            await self.set_session(session_id, session)
            return "proctor_agent"

        if phase == SessionPhase.TESTING.value:
            await self.set_session(session_id, session)
            return "proctor_agent"

        # FAST PATH: Deterministic routing for navigation intents to bypass Gemini
        if action in {"start", "next_topic", "next_step", "continue", "ready"}:
            agent_name = "diagnostic_agent" if phase == SessionPhase.PRACTICE.value else "tutor_agent"
            await self.set_session(session_id, session)
            return agent_name

        prompt = self.ORCHESTRATOR_ROUTING_PROMPT.format(
            active_phase=phase,
            current_topic=session.current_topic or "General",
            user_message=message_text
        )
        
        try:
            raw_route = await asyncio.to_thread(generate_response, prompt)
            agent_name = str(raw_route or "").replace("```", "").strip().lower()
            if agent_name not in {"tutor_agent", "diagnostic_agent", "proctor_agent"}:
                agent_name = "diagnostic_agent" if phase == SessionPhase.PRACTICE.value else "tutor_agent"
        except Exception as error:
            print(f"Orchestrator routing LLM failed: {error}")
            agent_name = "diagnostic_agent" if phase == SessionPhase.PRACTICE.value else "tutor_agent"

        if agent_name == "diagnostic_agent" and phase == SessionPhase.TEACHING.value:
            self._set_active_phase(session, SessionPhase.PRACTICE)

        await self.set_session(session_id, session)
        return agent_name
