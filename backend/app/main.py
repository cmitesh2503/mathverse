import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import os
import json
import asyncio
from base64 import b64decode

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .api.routes import session
from .tutor_brain.tutor_engine import TutorEngine
from .tutor_brain.lesson_state import LessonState
from .services.ai_gateway import stream_response
from .core.stream_manager import (
    start_stream,
    cancel_stream,
    is_cancelled,
    end_stream
)
import json
import asyncio

# 🚀 Tutor engine now handles all message logic and off-topic detection
# Removed: is_on_topic(), decide_mode() - tutor engine is the single source of truth

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
app = FastAPI(title="MathVerse API")

app.include_router(session.router)

# Google Cloud Speech-to-Text Bidi (optional)
speech_client = None
speech = None
try:
    from google.cloud import speech_v1p1beta1 as speech
    speech_client = speech.SpeechClient()
except Exception:
    try:
        from google.cloud import speech
        speech_client = speech.SpeechClient()
    except Exception as e:
        speech_client = None
        print("Google Cloud speech unavailable:", e)


tutor_engine = TutorEngine()

USE_STREAMING = True  # 🔥 Feature flag


def transcribe_audio_chunk(base64_data):
    if not speech_client:
        return None

    try:
        audio_content = b64decode(base64_data)
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            profanity_filter=False,
        )

        response = speech_client.recognize(config=config, audio=audio)
        if response.results:
            return response.results[-1].alternatives[0].transcript

    except Exception as e:
        print("STT transcription error:", e)

    return None


@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await websocket.accept()

    # 🎓 Auto-start lesson like a real classroom teacher
    session_id = "default_session"  # Use default session for auto-start
    grade = 10  # Default grade

    # Initialize session if needed
    if session_id not in tutor_engine.sessions:
        tutor_engine.sessions[session_id] = LessonState()
    tutor_engine.sessions[session_id].grade = grade

    # 🚀 Auto-start the topic introduction
    if USE_STREAMING:
        try:
            start_stream(session_id)
            response = tutor_engine.process(session_id, "")  # Empty message to trigger auto-start

            await websocket.send_json({"type": "start"})

            for word in response.split():
                if is_cancelled(session_id):
                    break
                await websocket.send_json({
                    "type": "chunk",
                    "content": word + " "
                })
                await asyncio.sleep(0.03)

            await websocket.send_json({"type": "done"})
            end_stream(session_id)

        except Exception as e:
            print(f"Auto-start streaming error: {e}")
            # Fallback to non-streaming
            response = tutor_engine.process(session_id, "")
            await websocket.send_json({"type": "explanation", "content": response})

    else:
        response = tutor_engine.process(session_id, "")
        await websocket.send_json({"type": "explanation", "content": response})

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

            session_id = data.get("session_id", "test123")
            grade = data.get("grade", 10)

            message = None
            if data.get("type") == "audio_chunk" and "data" in data:
                transcript = transcribe_audio_chunk(data["data"])
                if transcript:
                    message = transcript
                    # send transcript back to client for transparency
                    await websocket.send_json({"type": "transcript", "content": transcript})
                else:
                    print("Audio chunk could not be transcribed")
                    continue
            elif "message" in data:
                message = data["message"]

            if not message:
                print("No valid message in payload:", data)
                continue

            print("WS INPUT:", message)

            # Set grade in session
            if session_id not in tutor_engine.sessions:
                tutor_engine.sessions[session_id] = LessonState()
            tutor_engine.sessions[session_id].grade = grade

            # 🚨 Cancel any previous stream
            cancel_stream(session_id)

            # 👉 STREAMING ENABLED
            if USE_STREAMING:
                try:
                    # 🆕 Start new stream
                    start_stream(session_id)

                    # 🧠 Get response from TutorEngine (this handles everything now)
                    response = tutor_engine.process(session_id, message)

                    if not response:
                        response = "Let’s solve it step by step 😊"

                    # 🚀 Start streaming (simple MVP)
                    await websocket.send_json({"type": "start"})

                    for word in response.split():
                        if is_cancelled(session_id):
                            break

                        await websocket.send_json({
                            "type": "chunk",
                            "content": word + " "
                        })

                        await asyncio.sleep(0.03)

                    await websocket.send_json({"type": "done"})
                    end_stream(session_id)

                except Exception as e:
                    print(f"Streaming error: {e}")
                    # Fallback to non-streaming
                    response = tutor_engine.process(session_id, message)
                    if not response:
                        response = "Let’s solve it step by step 😊"
                    await websocket.send_json({"type": "explanation", "content": response})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=True)