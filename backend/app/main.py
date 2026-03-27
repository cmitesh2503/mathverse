from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from backend.app.api.routes import session
from backend.app.tutor_brain.tutor_engine import TutorEngine
from backend.app.services.ai_gateway import stream_response
from backend.app.core.stream_manager import (
    start_stream,
    cancel_stream,
    is_cancelled,
    end_stream
)
from backend.app.agents.teacher_agent import decide_mode
import json
import asyncio

app = FastAPI(title="MathVerse API")

app.include_router(session.router)

tutor_engine = TutorEngine()

USE_STREAMING = True  # 🔥 Feature flag


@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # 📥 Receive raw message
            raw_data = await websocket.receive_text()
            print("RAW DATA:", raw_data)

            # 🔄 Parse JSON safely
            try:
                data = json.loads(raw_data)
            except Exception:
                print("Invalid JSON received:", raw_data)
                continue

            # 🛡️ Validate payload
            if isinstance(data, str):
                print("Received raw string, converting to message")
                data = {
                    "session_id": "test123",  # default session
                    "message": data
                }

            elif not isinstance(data, dict):
                print("Invalid payload:", data)
                continue

            if "session_id" not in data or "message" not in data:
                print("Missing keys:", data)
                continue

            session_id = data["session_id"]
            message = data["message"]

            print("WS INPUT:", message)

            # 🚨 Cancel any previous stream
            cancel_stream(session_id)

            # 👉 STREAMING ENABLED
            if USE_STREAMING:
                try:
                    # 🆕 Start new stream
                    start_stream(session_id)

                    # 🧠 Decide mode
                    mode = decide_mode(message, "current_state")
                    print("MODE:", mode)

                    # 🚨 BREAK mode (no streaming)
                    if mode == "BREAK":
                        await websocket.send_json({
                            "type": "info",
                            "content": "Okay, let's take a short break 👍"
                        })
                        end_stream(session_id)
                        continue

                    # 🎯 Prompt selection
                    if mode == "DOUBT":
                        prompt = f"Answer this doubt clearly: {message}"
                    else:
                        prompt = tutor_engine.build_prompt(session_id, message)

                    # 🧪 Safety check
                    if not isinstance(prompt, str):
                        raise ValueError(f"Invalid prompt: {prompt}")

                    # 🚀 Start streaming
                    await websocket.send_json({"type": "start"})

                    async for chunk in stream_response(prompt):
                        await asyncio.sleep(0.1)
                        # 🔴 Stop if interrupted
                        if is_cancelled(session_id):
                            print("STREAM CANCELLED")
                            await websocket.send_json({"type": "done"})
                            break

                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })

                    # ✅ Cleanup
                    end_stream(session_id)

                    await websocket.send_json({"type": "done"})

                except Exception as e:
                    print("Streaming failed, fallback:", e)

                    end_stream(session_id)

                    # 🔁 FALLBACK to non-streaming
                    response = tutor_engine.process(session_id, message)

                    if not response:
                        response = "Let’s solve it step by step 😊"

                    await websocket.send_json({
                        "type": "explanation",
                        "content": response
                    })

            # 👉 STREAMING DISABLED
            else:
                response = tutor_engine.process(session_id, message)

                if not response:
                    response = "Let’s solve it step by step 😊"

                await websocket.send_json({
                    "type": "explanation",
                    "content": response
                })

    except WebSocketDisconnect:
        print("Client disconnected")