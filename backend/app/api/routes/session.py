from fastapi import APIRouter
import uuid

router = APIRouter(prefix="/session", tags=["Session"])

# Temporary in-memory store
sessions = {}

@router.post("/start")
def start_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"messages": []}
    return {"session_id": session_id}


@router.post("/message")
def send_message(data: dict):
    session_id = data.get("session_id")
    message = data.get("message")

    if session_id not in sessions:
        return {"error": "Invalid session"}

    sessions[session_id]["messages"].append(message)

    return {
        "response": "Hello, I am your MathVerse tutor"
    }