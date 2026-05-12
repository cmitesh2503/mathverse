import asyncio
import contextlib
import base64
import json
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
    from .services.live_tutor_service import LiveTutorBridge

    print("Tutor WebSocket connected")

    start_request = _session_request_from_socket(websocket)
    session_record = session_service.create_or_resume_session(start_request)
    session_id = session_record.session_id
    live_bridge = LiveTutorBridge(session_id, websocket.send_json)
    live_connected = False

    async def ensure_live_bridge() -> bool:
        nonlocal live_connected

        if live_connected:
            return True

        if not live_api_available() or not live_bridge.available:
            return False

        try:
            live_connected = await live_bridge.connect()
        except Exception as error:  # pragma: no cover - network dependent
            print(f"Gemini Live connect failed: {error}")
            live_connected = False
        return live_connected

    with contextlib.suppress(Exception):
        live_connected = await ensure_live_bridge()

    await websocket.send_json(
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
    )
    await websocket.send_json(
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
    )
    await websocket.send_json(
        {
            "type": "state",
            "state": live_bridge.current_state(),
        }
    )

    #asyncio.create_task(asyncio.to_thread(init_cbse))

    if not session_record.transcript:
        await live_bridge.send_text_turn("ready")

    try:
        while True:
            raw_data = await websocket.receive_text()
            print("📩 RAW:", raw_data)
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            message = None
            if payload.get("type") == "live_input_audio" and payload.get("data"):
                if await ensure_live_bridge():
                    await live_bridge.send_audio_chunk(
                        base64.b64decode(payload["data"])
                    )
                    continue
                await websocket.send_json(
                    {
                        "type": "live_warning",
                        "content": "Native Gemini audio is not connected right now.",
                    }
                )
                continue
            if payload.get("type") == "audio_stream_end":
                if await ensure_live_bridge():
                    await live_bridge.end_audio_stream()
                continue
            if payload.get("type") == "interrupt":
                cancel_stream(session_id)
                end_stream(session_id)
                await websocket.send_json({"type": "squelch"})
                if live_connected:
                    with contextlib.suppress(Exception):
                        await live_bridge.close()
                    await websocket.send_json(
                        {
                            "type": "live_warning",
                            "content": "Stopped live audio so you can speak.",
                        }
                    )
                    live_connected = False
                await websocket.send_json({"type": "assistant_turn_complete", "reason": "interrupted"})
                continue
            if payload.get("message"):
                message = payload["message"]

            if not message:
                continue

            if live_connected:
                await live_bridge.send_text_turn(message)
                continue

            cancel_stream(session_id)
            await live_bridge.send_text_turn(message)

    except WebSocketDisconnect:
        print("Tutor WebSocket disconnected")
        end_stream(session_id)
    finally:
        await live_bridge.close()
            
@app.on_event("startup")
async def startup_event():
    print("MathVerse multi-agent backend ready.")
            
@app.get("/homework/{student_id}")
def fetch_homework(student_id: str):
    return get_homework(student_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, reload=True)
