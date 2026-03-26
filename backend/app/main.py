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

app = FastAPI(title="MathVerse API")

app.include_router(session.router)

tutor_engine = TutorEngine()


USE_STREAMING = True  # 🔥 toggle here (very important)

@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            session_id = data["session_id"]
            message = data["message"]

            print("WS INPUT:", message)

            # 🚨 ALWAYS cancel any previous stream first
            cancel_stream(session_id)

            # 👉 STREAMING PATH
            if USE_STREAMING:
                try:
                    # 🆕 Start new stream
                    start_stream(session_id)

                    await websocket.send_json({"type": "start"})

                    prompt = tutor_engine.build_prompt(session_id, message)

                    # 🧪 Safety check (prevents your Ellipsis bug again)
                    if not isinstance(prompt, str):
                        raise ValueError(f"Invalid prompt: {prompt}")

                    async for chunk in stream_response(prompt):

                        # 🔴 STOP if user interrupted
                        if is_cancelled(session_id):
                            print("STREAM CANCELLED")
                            break

                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })

                    # ✅ Clean up stream state
                    end_stream(session_id)

                    await websocket.send_json({"type": "done"})

                except Exception as e:
                    print("Streaming failed, falling back:", e)

                    end_stream(session_id)  # ⚠️ important cleanup

                    # 🔁 FALLBACK TO OLD LOGIC
                    response = tutor_engine.process(session_id, message)

                    if not response:
                        response = "Let’s solve it step by step 😊"

                    await websocket.send_json({
                        "type": "explanation",
                        "content": response
                    })

            # 👉 NON-STREAMING (OR DISABLED)
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