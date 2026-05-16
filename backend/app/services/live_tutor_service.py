from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import re
from datetime import timedelta
from contextlib import AsyncExitStack
from typing import Awaitable, Callable

from ..core.config import (
    GEMINI_LIVE_INPUT_LANGUAGE,
    GEMINI_LIVE_MODEL,
    GEMINI_LIVE_OUTPUT_LANGUAGE,
    GEMINI_LIVE_VOICE,
)
from ..services.ai_gateway import get_live_client, live_api_available
from ..services.cbse_exercises import build_exercise_solution
from ..services.rag_service import retrieve_context as rag_get_context
from ..services.retrieval_service import retrieve_context
from ..services.session_service import session_service
from ..tutor_brain.curriculum import get_grade_curriculum

try:
    from app.agents.diagnostic_agent import DiagnosticAgent
    from app.agents.orchestrator import Orchestrator
    from app.agents.proctor_agent import ProctorAgent
    from app.agents.teacher_agent import TutorAgent
    from app.models.session import StudentSession, utc_now
except ModuleNotFoundError:
    from ..agents.diagnostic_agent import DiagnosticAgent
    from ..agents.orchestrator import Orchestrator
    from ..agents.proctor_agent import ProctorAgent
    from ..agents.teacher_agent import TutorAgent
    from ..models.session import StudentSession, utc_now

try:
    from google.genai import types as live_types
except ImportError:  # pragma: no cover - optional dependency
    live_types = None


EventSink = Callable[[dict], Awaitable[None]]

LIVE_INPUT_SAMPLE_RATE = 16000
LIVE_OUTPUT_SAMPLE_RATE = 24000
CLASS_SESSION_MINUTES = 45


class LiveTutorBridge:
    def __init__(self, session_id: str, emit_event: EventSink):
        self.session_id = session_id
        self.emit_event = emit_event
        self._client = get_live_client()
        self._exit_stack = AsyncExitStack()
        self._live_session = None
        self._receiver_task: asyncio.Task | None = None
        self._send_lock = asyncio.Lock()
        self._assistant_started = False
        self._assistant_transcript = ""
        self._assistant_fallback = ""
        self._input_transcript = ""
        self._active_mode: str | None = None
        self._active_context: dict | None = None
        self._pending_transport: str | None = None
        self._closed = False
        self.orchestrator = Orchestrator()
        self.tutor_agent = TutorAgent()
        self.diagnostic_agent = DiagnosticAgent()
        self.proctor_agent = ProctorAgent()
        self.student_session = StudentSession(
            session_id=session_id,
            active_phase="teaching",
        )
        self.orchestrator.sessions[session_id] = self.student_session

    @property
    def available(self) -> bool:
        return bool(live_api_available() and self._client is not None and live_types is not None)

    async def connect(self) -> bool:
        if not self.available:
            return False

        session_record = session_service.get_session(self.session_id)
        if not session_record:
            return False

        config = self._build_connect_config(session_record)
        connect_cm = self._client.aio.live.connect(
            model=GEMINI_LIVE_MODEL,
            config=config,
        )
        self._live_session = await self._exit_stack.enter_async_context(connect_cm)
        self._receiver_task = asyncio.create_task(self._receive_loop())
        await self.emit_event(
            {
                "type": "live_status",
                "content": "Gemini Live session connected.",
                "mode": "native-audio",
            }
        )
        
        return True

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        if self._receiver_task:
            self._receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receiver_task
        await self._exit_stack.aclose()

    async def send_text_turn(
        self,
        message: str,
        *,
        mode: str | None = None,
        context: dict | None = None,
    ) -> None:
        if mode:
            self._active_mode = mode
        if isinstance(context, dict) and context:
            self._active_context = dict(context)
        self._reset_pending_turn(transport="text")
        agent_turn = await self._process_agent_turn(
            message,
            transport="text",
            append_user=True,
            append_assistant=True,
            mode=mode,
            context=context,
        )
        await self._emit_agent_turn(agent_turn)

    def current_state(self) -> dict:
        self._sync_student_session()
        return self._build_agent_state([])

    async def send_audio_chunk(self, audio_bytes: bytes) -> None:
        if not self._live_session or not live_types:
            raise RuntimeError("Gemini Live session is not ready")

        if self._pending_transport != "audio":
            self._reset_pending_turn(transport="audio")

        async with self._send_lock:
            await self._live_session.send_realtime_input(
                audio=live_types.Blob(
                    data=audio_bytes,
                    mime_type=f"audio/pcm;rate={LIVE_INPUT_SAMPLE_RATE}",
                )
            )

    async def send_encoded_audio(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> None:
        if not self._live_session or not live_types:
            raise RuntimeError("Gemini Live session is not ready")

        if self._pending_transport != "audio":
            self._reset_pending_turn(transport="audio")

        async with self._send_lock:
            await self._live_session.send_realtime_input(
                audio=live_types.Blob(
                    data=audio_bytes,
                    mime_type=mime_type,
                )
            )

    async def send_video_frame(self, frame_bytes: bytes, mime_type: str = "image/jpeg") -> None:
        if not self._live_session or not live_types:
            return

        blob = live_types.Blob(data=frame_bytes, mime_type=mime_type)
        async with self._send_lock:
            try:
                await self._live_session.send_realtime_input(video=blob)
            except Exception:
                with contextlib.suppress(Exception):
                    await self._live_session.send_realtime_input(image=blob)

    async def end_audio_stream(self) -> None:
        if not self._live_session:
            return

        async with self._send_lock:
            await self._live_session.send_realtime_input(audio_stream_end=True)

    def _build_connect_config(self, session_record):
        memory_context = session_service.build_memory_context(self.session_id)
        topic_title = session_record.topic_title or "CBSE Mathematics"

        source_material = self._firebase_curriculum_context(
            grade=int(getattr(session_record, "grade", 10) or 10),
            exam=str(getattr(self.student_session, "exam", "cbse") or "cbse"),
            chapter=topic_title,
            topic=topic_title,
        ) or retrieve_context(topic_title, session_record.grade)
        curriculum_grounding = (
            f"Board: {session_record.board}\n"
            f"Subject: {session_record.subject}\n"
            f"Grade: {session_record.grade}\n"
            f"Current chapter: {topic_title}"
        )

        if source_material:
            source_material = source_material[:1800]
            curriculum_grounding += (
                "\n\nSource material from NCERT / CBSE PDF curriculum:\n"
                "Use this textbook-backed content when teaching this chapter.\n"
                f"{source_material}"
            )

        resolved_system_prompt = self.tutor_agent.SYSTEM_PROMPT.format(
            grade=session_record.grade,
            exam=(getattr(self.student_session, "exam", "cbse") or "cbse").upper(),
            is_new_chapter=not bool(getattr(session_record, "transcript", None)),
            rag_context=source_material or "No RAG context provided.",
        )

        agenda_list = getattr(self.student_session, "agenda", [])
        agenda_text = "\n".join(f"{i+1}. {topic}" for i, topic in enumerate(agenda_list)) if agenda_list else f"1. {topic_title}"

        system_prompt = (
            f"{resolved_system_prompt}\n\n"
            "LIVE AUDIO & CLASSROOM RULES:\n"
            "1. YOU ARE THE DRIVER: You are leading a continuous 45-minute class. DO NOT wait for the user to explicitly ask to move on.\n"
            "2. AUTO-TRANSITION: When a concept is fully explained and the student understands, seamlessly and automatically transition to the next topic on the agenda below.\n"
            f"CLASS AGENDA (Teach sequentially):\n{agenda_text}\n\n"
            "3. TEACHING FLOW: For each concept: Introduce it -> Explain the formula -> Walk through step-by-step examples -> Solve an exercise from the textbook with them.\n"
            "4. Keep each spoken turn short, slow, and interactive. Pause to ensure they are following before proceeding to the next step.\n"
            "5. Do not mention internal routing, diagnostics, or hidden nudges.\n\n"
            f"Current chapter focus: {topic_title}\n"
            f"Current classroom memory:\n{memory_context}\n\n"
            f"Curriculum grounding:\n{curriculum_grounding}"
        )

        return live_types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=live_types.Content(
                parts=[live_types.Part(text=system_prompt)]
            ),
            speech_config=live_types.SpeechConfig(
                language_code=GEMINI_LIVE_OUTPUT_LANGUAGE,
                voice_config=live_types.VoiceConfig(
                    prebuilt_voice_config=live_types.PrebuiltVoiceConfig(
                        voice_name=GEMINI_LIVE_VOICE
                    )
                ),
            ),
            input_audio_transcription=live_types.AudioTranscriptionConfig(),
            output_audio_transcription=live_types.AudioTranscriptionConfig(),
            realtime_input_config=live_types.RealtimeInputConfig(
                activity_handling=live_types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                turn_coverage=live_types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
                automatic_activity_detection=live_types.AutomaticActivityDetection(
                    prefix_padding_ms=20,
                    silence_duration_ms=300,
                )
            ),
            session_resumption=live_types.SessionResumptionConfig(handle=None),
            context_window_compression=live_types.ContextWindowCompressionConfig(
                trigger_tokens=24000,
                sliding_window=live_types.SlidingWindow(target_tokens=12000),
            ),
        )

    async def _process_agent_turn(
        self,
        message: str,
        *,
        transport: str,
        append_user: bool,
        append_assistant: bool,
        mode: str | None = None,
        context: dict | None = None,
    ) -> dict:
        self._sync_student_session()
        effective_mode = mode or self._active_mode
        effective_context = context if isinstance(context, dict) else self._active_context
        if not isinstance(effective_context, dict):
            effective_context = {}
        if effective_context.get("grade") is not None:
            try:
                self.student_session.grade = int(effective_context["grade"])
            except (TypeError, ValueError):
                pass
        self.student_session.exam = "jee" if str(effective_context.get("exam", self.student_session.exam)).lower() == "jee" else "cbse"
        action = self._extract_action_from_message(message)

        if effective_mode == "class":
            self._ensure_class_timer(action)
            if self._is_class_time_over() and action != "start":
                return self._class_expired_turn()

        route = await self.orchestrator.route_message(
            self.session_id,
            message,
            mode=effective_mode,
            context=effective_context,
        )
        self.student_session.current_topic = self._resolve_current_topic()
        nudge = None
        diagnostic_result = None
        proctor_payload = None
        tutor_payload = {"advance_topic": False}
        rag_context = ""

        if effective_mode == "class":
            topic = self._resolve_current_topic()
            normalized_exam = "jee" if str(self.student_session.exam or "").lower() == "jee" else "cbse"
            source_hint = (
                "JEE PYQ patterns, solved examples, and problem solving strategies"
                if normalized_exam == "jee"
                else "NCERT textbook concept explanations, worked examples, and exercise questions"
            )
            query = (
                f"Grade {getattr(self.student_session, 'grade', 10)} "
                f"{normalized_exam.upper()} Mathematics "
                f"chapter {self.student_session.chapter_name or topic} "
                f"topic {topic} {message} "
                f"{source_hint}"
            ).strip()
            try:
                rag_context = self._firebase_curriculum_context(
                    grade=int(getattr(self.student_session, "grade", 10) or 10),
                    exam=normalized_exam,
                    chapter=self.student_session.chapter_name or topic,
                    topic=topic,
                ) or rag_get_context(query=query, exam_type=normalized_exam, k=6)
            except Exception as error:
                print(f"Live RAG lookup failed ({type(error).__name__}): {error}")
                rag_context = ""

        if route == "proctor_agent":
            proctor_payload = await self.proctor_agent.process_message(
                self.student_session,
                message,
            )
            spoken_response = proctor_payload.get("spoken_response", "")
            whiteboard_actions = proctor_payload.get("whiteboard_actions", [])
        elif route == "diagnostic_agent":
            diagnostic_result = await self.diagnostic_agent.evaluate_answer(
                self.student_session,
                message,
                correct_answer="42",
            )
            nudge = diagnostic_result.get("hidden_nudge")
            if effective_mode == "class":
                candidates = self._extract_problem_candidates(rag_context)
                if candidates:
                    base_prob = candidates[self.student_session.questions_asked % len(candidates)]
                    nudge = "\n".join(
                        part
                        for part in [
                            nudge,
                            "SYSTEM INSTRUCTION: Solve at least one exercise question fully on the whiteboard "
                            "using short sequential 'draw_text' steps. "
                            f"Use this question if relevant: {base_prob}",
                        ]
                        if part
                    )
            tutor_payload = await self.tutor_agent.process_message(
                self.student_session,
                message,
                diagnostic_nudge=nudge,
                rag_context=rag_context,
            )
            spoken_response = tutor_payload.get("spoken_response", "")
            whiteboard_actions = tutor_payload.get("whiteboard_actions", [])
        else:
            # âœ… FIX 2: Explicitly order the AI Agent to solve the problem on the board
            if effective_mode == "class":
                candidates = self._extract_problem_candidates(rag_context)
                if candidates:
                    base_prob = candidates[self.student_session.questions_asked % len(candidates)]
                    nudge = (
                        (nudge or "")
                        + "\nSYSTEM INSTRUCTION: Solve at least one exercise question fully on the whiteboard "
                        "using short sequential 'draw_text' steps. "
                        f"Use this question if relevant: {base_prob}"
                    )

            tutor_payload = await self.tutor_agent.process_message(
                self.student_session,
                message,
                diagnostic_nudge=nudge,
                rag_context=rag_context,
            )
            spoken_response = tutor_payload.get("spoken_response", "")
            whiteboard_actions = tutor_payload.get("whiteboard_actions", [])

        if route != "proctor_agent" and tutor_payload.get("advance_topic"):
            next_topic = self.orchestrator._advance_to_next_topic(self.student_session)
            whiteboard_actions = [
                *whiteboard_actions,
                {"action": "draw_text", "content": f"Topic complete. Next topic: {next_topic}"},
            ]

        whiteboard_actions = self._prepare_problem_whiteboard_actions(
            topic=self._resolve_current_topic(),
            actions=whiteboard_actions,
            variation=self.student_session.questions_asked,
            rag_context=rag_context,
        )
        self.student_session.questions_asked += 1
        whiteboard_actions = self._ensure_board_header_actions(whiteboard_actions)

        if not self._has_action_text(whiteboard_actions):
            whiteboard_actions = self._topic_problem_actions(
                topic=self._resolve_current_topic(),
                variation=self.student_session.questions_asked,
                rag_context=rag_context,
            )
            whiteboard_actions = self._ensure_board_header_actions(whiteboard_actions)
        spoken_response = self._spoken_from_actions(
            spoken_response=spoken_response,
            whiteboard_actions=whiteboard_actions,
            topic=self._resolve_current_topic(),
        )
        state = self._build_agent_state(whiteboard_actions)

        if append_user:
            session_service.append_turn(
                self.session_id,
                "user",
                message,
                transport=transport,
            )

        if append_assistant and spoken_response:
            session_service.append_turn(
                self.session_id,
                "assistant",
                spoken_response,
                transport=transport,
            )

        session_service.update_session_metadata(
            self.session_id,
            {
                "student_session": self.student_session.model_dump(mode="json"),
                "last_agent_route": route,
                "last_diagnostic": diagnostic_result,
                "last_proctor": proctor_payload,
                "whiteboard_actions": whiteboard_actions,
                "whiteboard": state["whiteboard"],
            },
        )

        return {
            "route": route,
            "spoken_response": spoken_response,
            "whiteboard_actions": whiteboard_actions,
            "diagnostic": diagnostic_result,
            "state": state,
            "archive": self._session_archive(),
            "session_time_left_seconds": self._class_time_left_seconds() if effective_mode == "class" else None,
            "session_duration_seconds": int(self.student_session.class_duration_minutes * 60) if effective_mode == "class" else None,
            "session_expired": False,
        }

    async def _emit_agent_turn(self, agent_turn: dict) -> None:
        await self._ensure_assistant_started()
        await self.emit_event(
            {
                "type": "assistant_text",
                "content": agent_turn["spoken_response"],
            }
        )
        await self.emit_event(
            {
                "type": "whiteboard_actions",
                "actions": agent_turn["whiteboard_actions"],
            }
        )
        await self.emit_event(
            {
                "type": "assistant_turn_complete",
                "spoken_response": agent_turn["spoken_response"],
                "whiteboard_actions": agent_turn["whiteboard_actions"],
                "state": agent_turn["state"],
                "archive": agent_turn["archive"],
                "session_time_left_seconds": agent_turn.get("session_time_left_seconds"),
                "session_duration_seconds": agent_turn.get("session_duration_seconds"),
                "session_expired": agent_turn.get("session_expired", False),
            }
        )
        self._pending_transport = None
        self._assistant_started = False
        self._assistant_transcript = ""
        self._assistant_fallback = ""
        self._input_transcript = ""

    def _sync_student_session(self) -> None:
        session = self.orchestrator.get_or_create_session(self.session_id)
        self.student_session = session
        session_record = session_service.get_session(self.session_id)
        if session_record and session_record.topic_title and not self.student_session.current_topic:
            self.student_session.current_topic = session_record.topic_title
        if session_record and session_record.grade:
            self.student_session.grade = int(session_record.grade)

    def _resolve_current_topic(self) -> str:
        if self.student_session.current_topic:
            return str(self.student_session.current_topic)
        if self.student_session.agenda and 0 <= self.student_session.current_topic_index < len(self.student_session.agenda):
            return str(self.student_session.agenda[self.student_session.current_topic_index])
        return str(self.student_session.chapter_name or "Current Topic")

    def _ensure_board_header_actions(self, actions: list[dict]) -> list[dict]:
        chapter = str(self.student_session.chapter_name or "Current Chapter")
        topic = self._resolve_current_topic()
        has_chapter = False
        has_topic = False
        for action in actions:
            text = self._action_text(action).lower()
            if text.startswith("chapter:"):
                has_chapter = True
            if text.startswith("topic:"):
                has_topic = True

        header: list[dict] = []
        if not has_chapter:
            header.append({"action": "draw_text", "content": f"Chapter: {chapter}"})
        if not has_topic:
            header.append({"action": "draw_text", "content": f"Topic: {topic}"})
        if not header:
            return actions
        return [*header, *actions]

    def _build_agent_state(self, whiteboard_actions: list[dict]) -> dict:
        chalk_lines = []
        for action in whiteboard_actions:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("action") or "").strip().lower()
            if action_name in {"clear", "clear_board", "erase", "reset_board"}:
                continue
            content = (
                action.get("content")
                or action.get("text")
                or action.get("value")
                or action.get("message")
                or action.get("expression")
                or action.get("label")
            )
            if isinstance(content, str) and content.strip():
                chalk_lines.append(content.strip())

        chapter_title = self.student_session.chapter_name or self._resolve_current_topic()
        topic_title = self._resolve_current_topic()

        return {
            "stage": self.student_session.active_phase,
            "topic_title": topic_title,
            "difficulty_level": self.student_session.difficulty_level,
            "mistake_history": self.student_session.mistake_history,
            "current_problem": self.student_session.current_problem,
            "whiteboard_actions": whiteboard_actions,
            "whiteboard": {
                "title": f"{chapter_title} | {topic_title}",
                "subtitle": "Arvind Sir's smart blackboard",
                "chalk_lines": chalk_lines,
                "actions": whiteboard_actions,
            },
        }

    def _session_archive(self) -> list[dict]:
        session_record = session_service.get_session(self.session_id)
        return session_service.list_sessions(
            session_record.student_id if session_record else "local-student",
            session_record.grade if session_record else None,
        )

    def _reset_pending_turn(self, transport: str) -> None:
        self._pending_transport = transport
        self._assistant_started = False
        self._assistant_transcript = ""
        self._input_transcript = ""

    async def _receive_loop(self) -> None:
        try:
            async for message in self._live_session.receive():
                await self._handle_message(message)
        except asyncio.CancelledError:  # pragma: no cover - expected on shutdown
            raise
        except Exception as error:  # pragma: no cover - network dependent
            await self.emit_event(
                {
                    "type": "live_error",
                    "content": f"Gemini Live session stopped: {error}",
                }
            )

    async def _handle_message(self, message) -> None:
        if message.session_resumption_update:
            update = message.session_resumption_update
            updates = {
                "live_resumable": bool(update.resumable),
                "live_last_consumed_client_message_index": update.last_consumed_client_message_index,
            }
            if update.new_handle:
                updates["live_resumption_handle"] = update.new_handle
            session_service.update_session_metadata(self.session_id, updates)

        if message.go_away:
            await self.emit_event(
                {
                    "type": "live_warning",
                    "content": "Gemini Live will reconnect soon.",
                    "time_left": message.go_away.time_left,
                }
            )

        server_content = getattr(message, "server_content", None)
        if not server_content:
            return

        input_transcription = getattr(server_content, "input_transcription", None)
        if input_transcription and input_transcription.text:
            self._input_transcript = self._merge_transcript(
                self._input_transcript,
                input_transcription.text,
            )
            await self.emit_event(
                {
                    "type": "transcript",
                    "content": self._input_transcript,
                    "finished": bool(input_transcription.finished),
                }
            )

        output_transcription = getattr(server_content, "output_transcription", None)
        if output_transcription and output_transcription.text:
            await self._ensure_assistant_started()
            delta = self._delta_text(self._assistant_transcript, output_transcription.text)
            if delta:
                self._assistant_transcript += delta
                await self.emit_event({"type": "assistant_text", "content": delta})

        audio_data = getattr(message, "data", None)
        if audio_data:
            await self._ensure_assistant_started()
            await self.emit_event(
                {
                    "type": "live_audio",
                    "data": base64.b64encode(audio_data).decode("ascii"),
                    "sample_rate": LIVE_OUTPUT_SAMPLE_RATE,
                }
            )

        if getattr(server_content, "turn_complete", False):
            await self._finalize_turn()

    async def _ensure_assistant_started(self) -> None:
        if self._assistant_started:
            return

        self._assistant_started = True
        await self.emit_event({"type": "assistant_turn_start"})

    async def _finalize_turn(self) -> None:
        agent_turn = None

        if not self._assistant_transcript and self._assistant_fallback:
            await self._ensure_assistant_started()
            self._assistant_transcript = self._assistant_fallback
            await self.emit_event(
                {"type": "assistant_text", "content": self._assistant_fallback}
            )

        if self._pending_transport == "audio" and self._input_transcript.strip():
            agent_turn = await self._process_agent_turn(
                self._input_transcript.strip(),
                transport="bidi",
                append_user=True,
                append_assistant=False,
            )
            await self.emit_event(
                {
                    "type": "user_turn",
                    "content": self._input_transcript.strip(),
                    "transport": "bidi",
                }
            )
            await self.emit_event(
                {
                    "type": "whiteboard_actions",
                    "actions": agent_turn["whiteboard_actions"],
                }
            )

            if not self._assistant_transcript.strip():
                await self._ensure_assistant_started()
                self._assistant_transcript = agent_turn["spoken_response"]
                await self.emit_event(
                    {
                        "type": "assistant_text",
                        "content": self._assistant_transcript,
                    }
                )

        if self._assistant_transcript.strip():
            session_service.append_turn(
                self.session_id,
                "assistant",
                self._assistant_transcript.strip(),
                transport="bidi" if self._pending_transport == "audio" else "text",
            )

        state = agent_turn["state"] if agent_turn else self._build_agent_state([])
        await self.emit_event(
            {
                "type": "assistant_turn_complete",
                "spoken_response": self._assistant_transcript.strip(),
                "whiteboard_actions": agent_turn["whiteboard_actions"] if agent_turn else [],
                "state": state,
                "archive": self._session_archive(),
                "session_time_left_seconds": agent_turn.get("session_time_left_seconds") if agent_turn else None,
                "session_duration_seconds": agent_turn.get("session_duration_seconds") if agent_turn else None,
                "session_expired": agent_turn.get("session_expired", False) if agent_turn else False,
            }
        )
        self._pending_transport = None
        self._assistant_started = False
        self._assistant_transcript = ""
        self._assistant_fallback = ""
        self._input_transcript = ""

    def _merge_transcript(self, current: str, incoming: str) -> str:
        incoming = incoming.strip()
        if not current:
            return incoming
        if incoming.startswith(current):
            return incoming
        if current.endswith(incoming):
            return current
        return f"{current} {incoming}".strip()

    def _delta_text(self, current: str, incoming: str) -> str:
        incoming = incoming.strip()
        if not incoming:
            return ""
        if not current:
            return incoming
        if incoming.startswith(current):
            return incoming[len(current) :].lstrip()
        if current.endswith(incoming):
            return ""
        return incoming

    def _action_text(self, action: dict[str, object]) -> str:
        action_name = str(action.get("action") or "").strip().lower()
        if action_name in {"clear", "clear_board", "erase", "reset_board"}:
            return ""
        text = (
            action.get("content")
            or action.get("text")
            or action.get("value")
            or action.get("message")
            or action.get("expression")
            or action.get("label")
            or ""
        )
        return str(text).strip()

    def _spoken_from_actions(
        self,
        spoken_response: str,
        whiteboard_actions: list[dict[str, object]],
        topic: str,
    ) -> str:
        spoken = str(spoken_response or "").strip()
        if spoken:
            return spoken
        lines = [self._action_text(action) for action in whiteboard_actions if isinstance(action, dict)]
        lines = [line for line in lines if line]
        if lines:
            return " ".join(lines[:4])
        return (
            f"We finished the current board steps for {topic}. "
            "Click Next when you are ready for the next explanation."
        )

    def _is_greeting_line(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            phrase in lowered
            for phrase in (
                "welcome",
                "hello",
                "good morning",
                "good evening",
                "welcome back",
            )
        )

    def _is_symbolic_math(self, text: str) -> bool:
        value = str(text or "").strip()
        lowered = value.lower()
        if not value:
            return False

        keyword_hits = (
            "subset",
            "superset",
            "union",
            "intersection",
            "cartesian",
            "roster",
            "set-builder",
            "domain",
            "range",
        )
        if any(keyword in lowered for keyword in keyword_hits):
            return True

        if any(token in value for token in ("=", "<=", ">=", "->", "=>", "^", "|", "{", "}")):
            return True

        if re.search(r"\b\d+\s*[-+*/]\s*\d+\b", value):
            return True

        if re.search(r"\(\s*[A-Za-z0-9]+\s*,\s*[A-Za-z0-9]+\s*\)", value):
            return True

        return False

    def _is_equation_line(self, text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        if "=" in value or "<=" in value or ">=" in value:
            return True
        if re.search(r"\b\d+\s*[-+*/]\s*\d+\b", value):
            return True
        if re.search(r"\b[A-Za-z]\s*\^", value):
            return True
        if re.search(r"\b[A-Za-z]\s*=\s*", value):
            return True
        return False

    def _needs_problem_board(self, actions: list[dict[str, object]]) -> bool:
        if not actions:
            return True

        # âœ… FIX 3: Trust the AI! If it returns more than 2 steps, it's solving the math!
        if len(actions) > 2:
            return False

        has_equation_action = any(
            str(action.get("action", "")).strip().lower()
            in {"write_equation", "plot_curve", "draw_coordinate_axes", "draw_line", "draw_circle"}
            for action in actions
            if isinstance(action, dict)
        )
        if has_equation_action:
            return False

        equation_count = 0
        symbolic_count = 0
        prose_count = 0
        for action in actions:
            text = self._action_text(action)
            if not text:
                continue
            if self._is_equation_line(text):
                equation_count += 1
            elif self._is_symbolic_math(text):
                symbolic_count += 1
            elif len(text.split()) >= 10:
                prose_count += 1

        if equation_count >= 1 and prose_count == 0:
            return False
        if symbolic_count >= 2:
            return False
        if symbolic_count == 1 and prose_count == 0:
            return False
        return True

    def _has_action_text(self, actions: list[dict[str, object]]) -> bool:
        return any(self._action_text(action) for action in actions if isinstance(action, dict))

    def _extract_problem_candidates(self, rag_context: str, limit: int = 8) -> list[str]:
        if not isinstance(rag_context, str) or not rag_context.strip():
            return []

        candidates: list[str] = []
        seen: set[str] = set()
        lines = re.split(r"[\r\n]+", rag_context)
        for raw_line in lines:
            line = str(raw_line or "").strip()
            if not line:
                continue

            line = re.sub(r"^\s*(q(?:uestion)?|ex(?:ample)?)\s*[\d.:-]*\s*", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\s+", " ", line).strip(" -:;")
            lowered = line.lower()
            if len(line) < 14 or len(line) > 220:
                continue
            if lowered.startswith("this theorem can be proved") or lowered.startswith("proof"):
                continue
            if lowered.endswith(("such", "therefore", "hence")):
                continue
            if not (
                "?" in line
                or any(
                    token in lowered
                    for token in (
                        "solve",
                        "find",
                        "evaluate",
                        "prove",
                        "show",
                        "simplify",
                        "determine",
                        "calculate",
                    )
                )
            ):
                continue

            key = lowered[:180]
            if key in seen:
                continue
            seen.add(key)
            candidates.append(line)
            if len(candidates) >= limit:
                break
        return candidates

    def _firebase_curriculum_context(self, *, grade: int, exam: str, chapter: str, topic: str) -> str:
        try:
            curriculum = get_grade_curriculum(int(grade or 10), "jee" if str(exam).lower() == "jee" else "cbse")
            chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
            if not isinstance(chapters, list) or not chapters:
                return ""

            chapter_l = str(chapter or "").strip().lower()
            topic_l = str(topic or "").strip().lower()
            chapter_match = None
            for item in chapters:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("chapter") or "").strip()
                slug = str(item.get("slug") or "").strip()
                title_l = title.lower()
                slug_l = slug.lower()
                if chapter_l and (chapter_l in title_l or title_l in chapter_l or chapter_l == slug_l):
                    chapter_match = item
                    break
                if topic_l and (topic_l in title_l or topic_l == slug_l):
                    chapter_match = item
                    break

            if not isinstance(chapter_match, dict):
                return ""

            lines: list[str] = []
            lines.append(f"Chapter: {chapter_match.get('title') or chapter_match.get('chapter') or chapter}")
            if chapter_match.get("summary"):
                lines.append(f"Summary: {chapter_match.get('summary')}")
            if chapter_match.get("teaching_anchor"):
                lines.append(f"Anchor: {chapter_match.get('teaching_anchor')}")
            if chapter_match.get("classroom_goal"):
                lines.append(f"Goal: {chapter_match.get('classroom_goal')}")
            for concept in chapter_match.get("concepts", [])[:6]:
                if not isinstance(concept, dict):
                    continue
                if concept.get("title"):
                    lines.append(f"Concept: {concept.get('title')}")
                if concept.get("definition"):
                    lines.append(f"Definition: {concept.get('definition')}")
                if concept.get("explanation"):
                    lines.append(f"Explanation: {concept.get('explanation')}")
                for bw in (concept.get("board_work") or [])[:4]:
                    lines.append(str(bw))
                for example in (concept.get("ncert_examples") or [])[:4]:
                    if isinstance(example, dict) and example.get("prompt"):
                        lines.append(f"Exercise question: {example.get('prompt')}")
                    for step in (example.get("steps") or [])[:5]:
                        lines.append(f"Step: {step}")
            context = "\n".join(str(line).strip() for line in lines if str(line).strip())
            return context if len(context) >= 200 else ""
        except Exception:
            return ""

    def _generate_similar_problem(self, problem: str, seed: int) -> str:
        if not problem:
            return "Solve a similar variation for this concept."

        delta = (abs(int(seed)) % 3) + 1

        def _replace(match: re.Match) -> str:
            value = int(match.group(0))
            adjusted = value + delta if value >= 0 else value - delta
            return str(adjusted)

        mutated = re.sub(r"(?<![A-Za-z])\d+(?![A-Za-z])", _replace, problem)
        if mutated == problem:
            return f"Solve a similar textbook variation of: {problem}"
        return mutated

    # âœ… FIX 4: Entirely removed fake dummy steps!
    def _pyq_problem_actions(self, topic: str, rag_context: str, variation: int = 0) -> list[dict]:
        sources = ["NCERT Textbook", "CBSE Exercise", "Similar Practice Problem"]
        source_label = sources[variation % len(sources)]
        candidates = self._extract_problem_candidates(rag_context)

        if candidates:
            base_problem = candidates[variation % len(candidates)]
        else:
            base_problem = f"Solve one step-by-step problem based on {topic or 'the current topic'}."

        if source_label == "Similar Practice Problem":
            prompt = self._generate_similar_problem(base_problem, variation + 1)
        elif source_label in ["NCERT Textbook", "CBSE Exercise"] and len(candidates) > 1:
            prompt = candidates[(variation + 1) % len(candidates)]
        else:
            prompt = base_problem

        solved = build_exercise_solution(
            {
                "chapter_title": topic or "Mathematics",
                "exercise": source_label,
                "number": str(variation + 1),
                "prompt": prompt,
            }
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()

        actions: list[dict] = [
            {"action": "draw_text", "content": f"Source: {source_label}"},
            {"action": "draw_text", "content": f"Problem: {prompt}"},
        ]
        for index, step in enumerate(solved_steps[:8], start=1):
            actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
        if answer:
            actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
        return actions

    def _topic_problem_actions(self, topic: str, variation: int = 0, rag_context: str = "") -> list[dict]:
        lowered = (topic or "").lower()
        alt = variation % 2

        if "set notation" in lowered or "representations" in lowered:
            if alt == 0:
                return [
                    {"action": "draw_text", "content": "Problem: Write B in roster form"},
                    {"action": "write_equation", "content": "B = {x in N | 2 <= x <= 6}"},
                    {"action": "write_equation", "content": "B = {2,3,4,5,6}"},
                    {"action": "draw_text", "content": "Now compare with A = {1,2,3,4,5}"},
                ]
            return [
                {"action": "draw_text", "content": "Problem: Convert roster to set-builder"},
                {"action": "write_equation", "content": "A = {3,6,9,12}"},
                {"action": "write_equation", "content": "A = {x in N | x = 3n, 1 <= n <= 4}"},
            ]

        if "subset" in lowered or "types of sets" in lowered:
            return [
                {"action": "draw_text", "content": "Problem: Check subset and proper subset"},
                {"action": "write_equation", "content": "A = {1,2,3}, B = {1,2,3,4,5}"},
                {"action": "write_equation", "content": "A subseteq B  (every element of A is in B)"},
                {"action": "write_equation", "content": "A subset B because A != B"},
            ]

        if "operation" in lowered:
            return [
                {"action": "draw_text", "content": "Problem: Find union, intersection, differences"},
                {"action": "write_equation", "content": "A = {1,2,3,4}, B = {3,4,5,6}"},
                {"action": "write_equation", "content": "A union B = {1,2,3,4,5,6}"},
                {"action": "write_equation", "content": "A intersection B = {3,4}"},
                {"action": "write_equation", "content": "A - B = {1,2},  B - A = {5,6}"},
            ]

        if "venn" in lowered:
            return [
                {"action": "draw_text", "content": "Problem: Students liking Cricket (C) and Football (F)"},
                {"action": "write_equation", "content": "n(U)=40, n(C)=22, n(F)=18, n(C intersection F)=10"},
                {"action": "write_equation", "content": "Only C = 22 - 10 = 12"},
                {"action": "write_equation", "content": "Only F = 18 - 10 = 8"},
                {"action": "write_equation", "content": "Neither = 40 - (12+10+8) = 10"},
            ]

        if "ordered pair" in lowered or "cartesian" in lowered:
            return [
                {"action": "draw_text", "content": "Problem: Form Cartesian product and a relation"},
                {"action": "write_equation", "content": "A = {1,2}, B = {a,b}"},
                {"action": "write_equation", "content": "A x B = {(1,a),(1,b),(2,a),(2,b)}"},
                {"action": "write_equation", "content": "R = {(1,a),(2,b)} subseteq A x B"},
            ]

        if "relation" in lowered:
            return [
                {"action": "draw_text", "content": "Problem: Check relation properties"},
                {"action": "write_equation", "content": "A = {1,2,3}, R = {(1,1),(2,2),(3,3),(1,2),(2,1)}"},
                {"action": "write_equation", "content": "Reflexive: Yes (all (a,a) present)"},
                {"action": "write_equation", "content": "Symmetric: Yes ((1,2) and (2,1))"},
                {"action": "write_equation", "content": "Transitive: Check pairs to conclude"},
            ]

        return self._pyq_problem_actions(topic=topic, rag_context=rag_context, variation=variation)

    def _prepare_problem_whiteboard_actions(
        self,
        topic: str,
        actions: list[dict[str, object]],
        variation: int,
        rag_context: str = "",
    ) -> list[dict]:
        cleaned: list[dict] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("action", "")).strip()
            if not action_name:
                continue
            text = self._action_text(action)
            if text and self._is_greeting_line(text):
                continue
            is_text_action = action_name.lower() in {"write", "write_text", "add_text", "text", "draw_text"}
            if text and is_text_action and len(text.split()) >= 28 and not self._is_equation_line(text):
                structured = re.match(r"(?i)^(step\s*\d+|problem:|final answer:|source:|chapter:|topic:)", text)
                if not structured:
                    continue
            if action_name.lower() in {"write", "write_text", "add_text", "text"} and not text:
                continue
            cleaned.append(dict(action))

        if self._needs_problem_board(cleaned):
            return self._topic_problem_actions(topic, variation=variation, rag_context=rag_context)
        return cleaned

    def _extract_action_from_message(self, message: str) -> str:
        text = str(message or "").strip()
        lowered = text.lower()
        if lowered in {"start", "begin"}:
            return "start"
        if lowered in {"next", "next_step", "next topic", "next_topic"}:
            return "next"
        if text.startswith("{") and text.endswith("}"):
            try:
                payload = json.loads(text)
                if isinstance(payload, dict):
                    return str(payload.get("action", "")).strip().lower()
            except json.JSONDecodeError:
                return ""
        return ""

    def _ensure_class_timer(self, action: str) -> None:
        if action == "start" or self.student_session.class_started_at is None:
            self.student_session.class_started_at = utc_now()
            self.student_session.class_duration_minutes = CLASS_SESSION_MINUTES

    def _class_time_left_seconds(self) -> int:
        if self.student_session.class_started_at is None:
            return int(CLASS_SESSION_MINUTES * 60)
        total_seconds = int(self.student_session.class_duration_minutes * 60)
        elapsed_seconds = int((utc_now() - self.student_session.class_started_at).total_seconds())
        return max(0, total_seconds - elapsed_seconds)

    def _is_class_time_over(self) -> bool:
        if self.student_session.class_started_at is None:
            return False
        return utc_now() >= self.student_session.class_started_at + timedelta(
            minutes=self.student_session.class_duration_minutes
        )

    def _class_expired_turn(self) -> dict:
        spoken_response = (
            f"Our {self.student_session.class_duration_minutes}-minute class session is complete for today. "
            "Great effort. Please review today's notes and start a new class to continue."
        )
        whiteboard_actions = [
            {"action": "draw_text", "content": f"Session complete ({self.student_session.class_duration_minutes} minutes)"},
            {"action": "draw_text", "content": "Review notes and start a new class session."},
        ]
        state = self._build_agent_state(whiteboard_actions)
        return {
            "route": "tutor_agent",
            "spoken_response": spoken_response,
            "whiteboard_actions": whiteboard_actions,
            "diagnostic": None,
            "state": state,
            "archive": self._session_archive(),
            "session_time_left_seconds": 0,
            "session_duration_seconds": int(self.student_session.class_duration_minutes * 60),
            "session_expired": True,
        }
