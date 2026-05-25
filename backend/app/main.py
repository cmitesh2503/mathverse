import asyncio
import contextlib
import base64
import json
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

#sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .api.routes import avatar, evaluation, session
from .core.stream_manager import cancel_stream, end_stream, is_cancelled, start_stream
from .services.firebase_service import get_homework
from .api.practice import router as practice_router
from .api.tutor import router as tutor_router

app = FastAPI(title="MathVerse API")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(practice_router,prefix="/practice")
app.include_router(session.router, prefix="/session")
#app.include_router(session.router)
app.include_router(avatar.router)
app.include_router(evaluation.router)
app.include_router(tutor_router, prefix="/api/tutor")
uploads_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evaluation_uploads")
os.makedirs(uploads_root, exist_ok=True)
app.mount("/uploads/evaluation", StaticFiles(directory=uploads_root), name="evaluation_uploads")


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "MathVerse API",
        "docs": "/docs",
        "session_start": "/session/start",
        "tutor_ask": "/api/tutor/ask",
        "tutor_ws": "/ws/tutor",
    }

async def send_streamed_text(
    websocket: WebSocket,
    session_id: str,
    content: str,
    *,
    state: dict | None = None,
    archive: list[dict] | None = None,
) -> None:
    start_stream(session_id)
    await websocket.send_json({"type": "start"})
    if state is not None:
        await websocket.send_json(
            {
                "type": "state",
                "state": state,
                "archive": archive,
            }
        )

    for word in content.split():
        if is_cancelled(session_id):
            break
        await websocket.send_json({"type": "chunk", "content": word + " "})
        await asyncio.sleep(0.02)

    await websocket.send_json(
        {
            "type": "done",
            "state": state,
            "archive": archive,
        }
    )
    end_stream(session_id)


def _session_request_from_socket(websocket: WebSocket):
    from .models.session import StartSessionRequest

    params = websocket.query_params
    requested_grade = params.get("grade", "10")
    try:
        grade = int(requested_grade)
    except ValueError:
        grade = 10

    return StartSessionRequest(
        student_id=params.get("student_id", "local-student"),
        grade=grade,
        board=params.get("board", "CBSE"),
        subject=params.get("subject", "Mathematics"),
        session_id=params.get("session_id"),
        topic_slug=params.get("topic_slug"),
        start_new=params.get("start_new", "false").lower() == "true",
    )


def _serialize_lesson_state(snapshot):
    if snapshot is None:
        return {}

    if hasattr(snapshot, "model_dump"):
        return snapshot.model_dump(mode="json")

    if hasattr(snapshot, "__dict__"):
        return snapshot.__dict__

    return dict(snapshot) if isinstance(snapshot, dict) else {}




@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await websocket.accept()

    from .services.session_service import session_service
    from .services.ai_gateway import live_api_available
    from .services.live_tutor_service import LiveTutorBridge, LiveTutorConnectionError, VoiceProcessor

    print("Tutor WebSocket connected")

    start_request = _session_request_from_socket(websocket)
    session_record = session_service.create_or_resume_session(start_request)
    session_id = session_record.session_id
    client_connected = True
    send_lock = asyncio.Lock()

    async def safe_send_json(payload: dict) -> bool:
        nonlocal client_connected
        if not client_connected:
            return False
        try:
            async with send_lock:
                await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            client_connected = False
            return False

    async def push_prefetched_class_problem() -> None:
        from .api.tutor import orchestrator

        while client_connected:
            try:
                session = await orchestrator.get_session(session_id)
                if session is None:
                    await asyncio.sleep(0.35)
                    continue
                if session.next_problem_actions:
                    # Keep prefetch internal. The classroom auto-flow requests one
                    # turn at a time after the current explanation finishes.
                    session.next_problem_actions = []
                    await orchestrator.set_session(session_id, session)
                await asyncio.sleep(0.35)
            except Exception as error:
                print(f"Tutor WebSocket push failed: {error}")
                break

    asyncio.create_task(push_prefetched_class_problem())

    live_bridge = LiveTutorBridge(session_id, safe_send_json)
    live_connected = False
    live_connect_retry_after = 0.0
    voice_processor = VoiceProcessor()
    initial_mode = (websocket.query_params.get("mode") or "").lower()
    initial_exam = (websocket.query_params.get("exam") or "").lower()
    with contextlib.suppress(Exception):
        live_bridge.student_session.grade = int(session_record.grade)
    live_bridge.student_session.exam = "jee" if initial_exam == "jee" else "cbse"
    
    # Seed chapter name and agenda to prevent Gemini Live connection handshake crashes.
    with contextlib.suppress(Exception):
        live_bridge.student_session.chapter_name = (
            getattr(session_record, "chapter_name", None)
            or getattr(session_record, "topic_title", None)
            or "Mathematics Overview"
        )
    with contextlib.suppress(Exception):
        live_bridge.student_session.current_topic = (
            getattr(session_record, "topic_title", None)
            or live_bridge.student_session.chapter_name
        )
    with contextlib.suppress(Exception):
        live_bridge.student_session.agenda = getattr(session_record, "agenda", [])

    async def ensure_live_bridge() -> bool:
        nonlocal live_connected, live_connect_retry_after

        if live_connected:
            return True

        if not live_api_available() or not live_bridge.available:
            return False
        loop_time = asyncio.get_running_loop().time()
        if loop_time < live_connect_retry_after:
            return False

        try:
            live_connected = await live_bridge.connect()
        except Exception as error:  # pragma: no cover - network dependent
            print(f"Gemini Live connect failed: {error}")
            live_connected = False
            live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
        return live_connected

    if not await safe_send_json(
        {
            "type": "session_meta",
            "session": session_service.serialize_session(session_record),
            "archive": session_service.list_sessions(session_record.student_id, session_record.grade),
            "live_capabilities": {
                "native_audio_ready": live_api_available(),
                "native_audio_connected": live_connected,
                "transport": "server-websocket",
            },
        }
    ):
        await live_bridge.close()
        return
    if not await safe_send_json(
        {
            "type": "history",
            "messages": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "transport": turn.transport,
                    "timestamp": turn.timestamp.isoformat(),
                }
                for turn in session_record.transcript
                if turn.role in {"user", "assistant"}
            ],
        }
    ):
        await live_bridge.close()
        return
    if not await safe_send_json(
        {
            "type": "state",
            "state": await live_bridge.current_state(),
        }
    ):
        await live_bridge.close()
        return

    #asyncio.create_task(asyncio.to_thread(init_cbse))

    if not (initial_mode == "exam" and initial_exam == "jee") and not session_record.transcript:
        bootstrap_context: dict[str, object] = {}
        if initial_exam:
            bootstrap_context["exam"] = initial_exam
        grade_param = websocket.query_params.get("grade")
        if grade_param is not None:
            with contextlib.suppress(ValueError):
                bootstrap_context["grade"] = int(grade_param)
        topic_slug_param = websocket.query_params.get("topic_slug")
        if topic_slug_param:
            bootstrap_context["chapter_slug"] = topic_slug_param
        if getattr(session_record, "topic_title", None):
            bootstrap_context["chapter"] = session_record.topic_title
            bootstrap_context["topic"] = session_record.topic_title
        bootstrap_context["phase"] = "teaching"
        await live_bridge.send_text_turn(
            json.dumps({"action": "start"}),
            mode=initial_mode or None,
            context=bootstrap_context or None,
        )

    try:
        while True:
            try:
                raw_data = await websocket.receive_text()
            except RuntimeError as error:
                client_connected = False
                print(f"Tutor WebSocket receive stopped: {error}")
                break
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                continue
            payload_type = str(payload.get("type") or "")
            if payload_type == "live_input_audio":
                print("Tutor WS RAW: live_input_audio")
            else:
                print("Tutor WS RAW:", raw_data[:300] + ("..." if len(raw_data) > 300 else ""))

            message = None
            if payload.get("type") == "context_update":
                live_bridge.update_context(payload)
                continue
            if payload.get("type") == "live_input_audio" and payload.get("data"):
                try:
                    audio_chunk = base64.b64decode(payload["data"])
                except Exception:
                    continue
                if not voice_processor.process_chunk(audio_chunk):
                    continue
                if await ensure_live_bridge():
                    try:
                        await live_bridge.send_audio_chunk(audio_chunk)
                        continue
                    except LiveTutorConnectionError as error:
                        print(f"Gemini Live audio disconnected: {error}")
                        live_connected = False
                        live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
                continue
            if payload.get("type") == "live_input_video" and payload.get("data"):
                if await ensure_live_bridge():
                    try:
                        await live_bridge.send_video_frame(
                            base64.b64decode(payload["data"]),
                            mime_type=str(payload.get("mime_type") or "image/jpeg"),
                        )
                    except LiveTutorConnectionError as error:
                        print(f"Gemini Live video disconnected: {error}")
                        live_connected = False
                        live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
                continue
            if payload.get("type") == "audio_stream_end":
                if await ensure_live_bridge():
                    try:
                        await live_bridge.end_audio_stream()
                    except LiveTutorConnectionError as error:
                        print(f"Gemini Live audio end failed: {error}")
                        live_connected = False
                        live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
                elif str(payload.get("transcript") or "").strip():
                    await live_bridge.send_text_turn(
                        str(payload.get("transcript")).strip(),
                        mode=payload.get("mode") or initial_mode or None,
                        context=payload.get("context") if isinstance(payload.get("context"), dict) else None,
                    )
                continue
            if payload.get("type") == "recorded_audio_buffer" and payload.get("data"):
                if await ensure_live_bridge():
                    try:
                        await live_bridge.send_encoded_audio(
                            base64.b64decode(payload["data"]),
                            mime_type=str(payload.get("mime_type") or "audio/webm"),
                        )
                        await live_bridge.end_audio_stream()
                    except LiveTutorConnectionError as error:
                        print(f"Gemini Live recorded audio disconnected: {error}")
                        live_connected = False
                        live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
                else:
                    if not await safe_send_json(
                        {
                            "type": "live_warning",
                            "content": "Native Gemini audio is not connected right now.",
                        }
                    ):
                        break
                continue
            if payload.get("type") == "control" and str(payload.get("action", "")).lower() == "stop_listening":
                transcript_fallback = str(payload.get("transcript") or "").strip()
                if await ensure_live_bridge():
                    try:
                        await live_bridge.end_audio_stream()
                    except LiveTutorConnectionError as error:
                        print(f"Gemini Live stop listening failed: {error}")
                        live_connected = False
                        live_connect_retry_after = asyncio.get_running_loop().time() + 15.0
                elif transcript_fallback:
                    await live_bridge.send_text_turn(
                        transcript_fallback,
                        mode=payload.get("mode") or initial_mode or None,
                        context=payload.get("context") if isinstance(payload.get("context"), dict) else None,
                    )
                if not await safe_send_json({"type": "listening_stopped"}):
                    break
                continue
            if payload.get("type") == "interrupt":
                cancel_stream(session_id)
                end_stream(session_id)
                if not await safe_send_json({"type": "squelch"}):
                    break
                if live_connected:
                    with contextlib.suppress(Exception):
                        await live_bridge.close()
                    if not await safe_send_json(
                        {
                            "type": "live_warning",
                            "content": "Stopped live audio so you can speak.",
                        }
                    ):
                        break
                    live_connected = False
                if not await safe_send_json({"type": "assistant_turn_complete", "reason": "interrupted"}):
                    break
                continue
            if payload.get("message"):
                message = payload["message"]
            elif payload.get("action"):
                message = json.dumps({"action": str(payload.get("action"))})
            mode = payload.get("mode") or initial_mode or None
            context = payload.get("context") if isinstance(payload.get("context"), dict) else None
            if context is None:
                context = {}
                if initial_exam:
                    context["exam"] = initial_exam
                grade_param = websocket.query_params.get("grade")
                if grade_param is not None:
                    with contextlib.suppress(ValueError):
                        context["grade"] = int(grade_param)
                topic_slug_param = websocket.query_params.get("topic_slug")
                if topic_slug_param:
                    context["chapter_slug"] = topic_slug_param
                if getattr(session_record, "topic_title", None):
                    context["chapter"] = session_record.topic_title
                    context["topic"] = session_record.topic_title
                if not context:
                    context = None

            if not message:
                continue

            if live_connected:
                await live_bridge.send_text_turn(message, mode=mode, context=context)
                continue

            cancel_stream(session_id)
            await live_bridge.send_text_turn(message, mode=mode, context=context)

    except WebSocketDisconnect:
        client_connected = False
        print("Tutor WebSocket disconnected")
        end_stream(session_id)
    finally:
        await live_bridge.close()
            
@app.on_event("startup")
async def startup_event():
    from .api.tutor import orchestrator

    try:
        ok = await orchestrator.verify_connection()
    except Exception as error:
        raise RuntimeError(f"Critical startup failure: Redis unreachable ({type(error).__name__}: {error})") from error
    if not ok:
        raise RuntimeError("Critical startup failure: Redis connection check failed.")
    print("MathVerse multi-agent backend ready.")
            
@app.get("/homework/{student_id}")
def fetch_homework(student_id: str):
    return get_homework(student_id)


if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("MATHVERSE_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(app, host="localhost", port=8000, reload=reload_enabled)
