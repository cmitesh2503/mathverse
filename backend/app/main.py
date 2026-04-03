import asyncio
import contextlib
import base64
import json
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .api.routes import avatar, session
from .core.stream_manager import cancel_stream, end_stream, is_cancelled, start_stream
from .models.session import StartSessionRequest
from .services.ai_gateway import live_api_available
from .services.live_tutor_service import LiveTutorBridge
from .services.session_service import session_service
from .tutor_brain.runtime import tutor_engine

load_dotenv()

app = FastAPI(title="MathVerse API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(session.router)
app.include_router(avatar.router)


async def send_streamed_text(websocket: WebSocket, session_id: str, content: str) -> None:
    start_stream(session_id)
    await websocket.send_json({"type": "start"})

    for word in content.split():
        if is_cancelled(session_id):
            break
        await websocket.send_json({"type": "chunk", "content": word + " "})
        await asyncio.sleep(0.02)

    await websocket.send_json({"type": "done"})
    end_stream(session_id)


def _session_request_from_socket(websocket: WebSocket) -> StartSessionRequest:
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


@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await websocket.accept()
    print("Tutor WebSocket connected")

    start_request = _session_request_from_socket(websocket)
    session_record = session_service.create_or_resume_session(start_request)
    session_id = session_record.session_id
    tutor_engine.hydrate_session(session_id, session_record)
    live_bridge = LiveTutorBridge(session_id, websocket.send_json)
    live_connected = False

    if live_bridge.available:
        try:
            live_connected = await live_bridge.connect()
        except Exception as error:  # pragma: no cover - network dependent
            print(f"Gemini Live connect failed: {error}")
            live_connected = False

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
            "state": tutor_engine.snapshot(session_id).model_dump(mode="json"),
        }
    )

    if not session_record.transcript:
        intro = tutor_engine.process(session_id, "", session_record=session_record)
        session_service.append_turn(session_id, "assistant", intro)
        session_service.update_lesson_snapshot(session_id, tutor_engine.snapshot(session_id))
        await send_streamed_text(websocket, session_id, intro)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            message = None
            if payload.get("type") == "live_input_audio" and payload.get("data"):
                if live_connected:
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
                if live_connected:
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
            session_service.append_turn(session_id, "user", message, "text")
            session_record = session_service.get_session(session_id)
            response = tutor_engine.process(session_id, message, session_record=session_record)
            session_service.append_turn(session_id, "assistant", response)
            snapshot = tutor_engine.snapshot(session_id)
            session_service.update_lesson_snapshot(session_id, snapshot)

            await send_streamed_text(websocket, session_id, response)
            await websocket.send_json(
                {
                    "type": "state",
                    "state": snapshot.model_dump(mode="json"),
                    "archive": session_service.list_sessions(
                        session_record.student_id if session_record else start_request.student_id,
                        start_request.grade,
                    ),
                }
            )

    except WebSocketDisconnect:
        print("Tutor WebSocket disconnected")
        end_stream(session_id)
    finally:
        await live_bridge.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, reload=True)
