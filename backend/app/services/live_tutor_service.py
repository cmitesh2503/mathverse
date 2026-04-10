from __future__ import annotations

import asyncio
import base64
import contextlib
import re
from contextlib import AsyncExitStack
from typing import Awaitable, Callable

from ..core.config import (
    GEMINI_LIVE_INPUT_LANGUAGE,
    GEMINI_LIVE_MODEL,
    GEMINI_LIVE_OUTPUT_LANGUAGE,
    GEMINI_LIVE_VOICE,
)
from ..services.ai_gateway import get_live_client, live_api_available
from ..services.session_service import session_service
from ..tutor_brain.curriculum import build_curriculum_grounding, get_topic
from ..tutor_brain.runtime import tutor_engine

try:
    from google.genai import types as live_types
except ImportError:  # pragma: no cover - optional dependency
    live_types = None


EventSink = Callable[[dict], Awaitable[None]]

LIVE_INPUT_SAMPLE_RATE = 16000
LIVE_OUTPUT_SAMPLE_RATE = 24000


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
        self._pending_transport: str | None = None
        self._closed = False

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

    async def send_text_turn(self, message: str) -> None:
        if not self._live_session or not live_types:
            raise RuntimeError("Gemini Live session is not ready")

        guidance = self._plan_turn(message)
        spoken_guidance = self._spokenize_guidance(guidance)
        self._reset_pending_turn(transport="text")
        self._assistant_fallback = guidance

        live_prompt = (
            f"Student message:\n{message}\n\n"
            "Internal lesson steering for Ava. Adapt this naturally; do not read it literally:\n"
            f"{spoken_guidance}\n\n"
            "Reply directly to the student in a warm, spoken classroom style. "
            "Keep it short, slow, and interactive. "
            "Speak about twenty percent slower than a normal conversation. "
            "Use natural pauses and only one or two ideas before you stop. "
            "Do not read headings, bullets, markdown, or labels aloud. "
            "Introduce the chapter smoothly like a teacher, then explain the idea conversationally. "
            "Sound like a human tutor in a live lesson, not a narrator reading notes. "
            "Do not mention this internal steering."
        )

        async with self._send_lock:
            await self._live_session.send_client_content(
                turns=live_types.Content(
                    role="user",
                    parts=[live_types.Part(text=live_prompt)],
                ),
                turn_complete=True,
            )

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

    async def end_audio_stream(self) -> None:
        if not self._live_session:
            return

        async with self._send_lock:
            await self._live_session.send_realtime_input(audio_stream_end=True)

    def _build_connect_config(self, session_record):
        memory_context = session_service.build_memory_context(self.session_id)
        topic = get_topic(session_record.grade, session_record.topic_slug)
        topic_title = topic["title"] if topic else session_record.topic_title or "CBSE Mathematics"

        system_prompt = (
            "You are Ava, a real-time CBSE mathematics tutor.\n"
            "Act like a live online teacher, not a generic chatbot.\n"
            "Teach only from CBSE NCERT curriculum grounding provided below for the student grade.\n"
            "Keep every explanation grounded in explicit chapter concepts, equations, and examples. Avoid vague answers.\n"
            "Sound warm, patient, and conversational, like a tutor on a live call.\n"
            "Use everyday spoken English that feels natural for an Indian classroom.\n"
            "Speak at moderate-to-low speed with clear pauses between ideas.\n"
            "Speak about twenty percent slower than a normal conversation.\n"
            "Keep each turn short unless the student asks for a full explanation.\n"
            "Usually explain one step, then pause and ask one small check-in question.\n"
            "Never sound like you are reading from slides, notes, markdown, or UI text.\n"
            "Each class is a 45-minute session: pace it as intro, concept teaching, guided practice, then recap.\n"
            "Open a new chapter like a teacher: welcome the student, say what they will learn today, and reassure them that you will solve it together.\n"
            "Use only two or three short spoken sentences at a time when possible.\n"
            "Do not sound ceremonial, corporate, or overly formal.\n"
            "When the student is confused, slow down and use one worked example.\n"
            "Refer naturally to the whiteboard, equations, graphs, and examples.\n"
            "Do not drift into non-maths small talk.\n\n"
            f"Current chapter focus: {topic_title}\n"
            f"Current classroom memory:\n{memory_context}\n\n"
            f"Curriculum grounding:\n{build_curriculum_grounding(session_record.grade)}"
        )

        resume_handle = None
        if session_record.metadata:
            resume_handle = session_record.metadata.get("live_resumption_handle")

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
            input_audio_transcription=live_types.AudioTranscriptionConfig(
                language_codes=[GEMINI_LIVE_INPUT_LANGUAGE, "hi-IN"]
            ),
            output_audio_transcription=live_types.AudioTranscriptionConfig(
                language_codes=[GEMINI_LIVE_OUTPUT_LANGUAGE]
            ),
            realtime_input_config=live_types.RealtimeInputConfig(
                activity_handling=live_types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                turn_coverage=live_types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
                automatic_activity_detection=live_types.AutomaticActivityDetection(
                    prefix_padding_ms=120,
                    silence_duration_ms=900,
                )
            ),
            session_resumption=live_types.SessionResumptionConfig(
                handle=resume_handle,
                transparent=True,
            ),
            context_window_compression=live_types.ContextWindowCompressionConfig(
                trigger_tokens=24000,
                sliding_window=live_types.SlidingWindow(target_tokens=12000),
            ),
        )

    def _spokenize_guidance(self, guidance: str) -> str:
        lines: list[str] = []
        for raw_line in guidance.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            line = line.replace("**", "")
            line = re.sub(r"^#{1,6}\s*", "", line)
            line = re.sub(r"^[-*]\s*", "", line)
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"\s+", " ", line)
            if line:
                lines.append(line)

        spoken = ". ".join(lines)
        spoken = spoken.replace("Today's class", "Today's lesson")
        return spoken[:1800]

    def _plan_turn(self, message: str) -> str:
        session = session_service.append_turn(
            self.session_id,
            "user",
            message,
            transport="text",
        )
        refreshed_session = session_service.get_session(self.session_id)
        guidance = tutor_engine.process(
            self.session_id,
            message,
            session_record=refreshed_session or session,
        )
        session_service.update_lesson_snapshot(
            self.session_id,
            tutor_engine.snapshot(self.session_id),
        )
        return guidance

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
        if not self._assistant_transcript and self._assistant_fallback:
            await self._ensure_assistant_started()
            self._assistant_transcript = self._assistant_fallback
            await self.emit_event(
                {"type": "assistant_text", "content": self._assistant_fallback}
            )

        if self._pending_transport == "audio" and self._input_transcript.strip():
            session_service.append_turn(
                self.session_id,
                "user",
                self._input_transcript.strip(),
                transport="bidi",
            )
            refreshed_session = session_service.get_session(self.session_id)
            tutor_engine.process(
                self.session_id,
                self._input_transcript.strip(),
                session_record=refreshed_session,
            )
            session_service.update_lesson_snapshot(
                self.session_id,
                tutor_engine.snapshot(self.session_id),
            )
            await self.emit_event(
                {
                    "type": "user_turn",
                    "content": self._input_transcript.strip(),
                    "transport": "bidi",
                }
            )

        if self._assistant_transcript.strip():
            session_service.append_turn(
                self.session_id,
                "assistant",
                self._assistant_transcript.strip(),
                transport="bidi" if self._pending_transport == "audio" else "text",
            )

        snapshot = tutor_engine.snapshot(self.session_id)
        session_service.update_lesson_snapshot(self.session_id, snapshot)
        session = session_service.get_session(self.session_id)
        await self.emit_event(
            {
                "type": "assistant_turn_complete",
                "state": snapshot.model_dump(mode="json"),
                "archive": session_service.list_sessions(
                    session.student_id if session else "local-student",
                    session.grade if session else None,
                ),
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
