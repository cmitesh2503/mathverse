from email import message

from fastapi import APIRouter
import uuid
from ...tutor_brain.tutor_engine import TutorEngine

tutor_engine = TutorEngine()

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
    
    print("API HIT /session/message")
    print("INPUT:", message)
    
    response = tutor_engine.process(session_id, message)
    print("output:", response)

    return {
        "response": response
    }