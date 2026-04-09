from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()

class SessionStartRequest(BaseModel):
    student_id: str
    grade: int
    session_id: str | None = None
    start_new: bool = False


@router.post("/start")
async def start_session(req: SessionStartRequest):
    session_id = req.session_id or str(uuid.uuid4())

    return {
        "session": {
            "session_id": session_id,
            "student_id": req.student_id,
            "title": "CBSE Mathematics Session",
            "board": "CBSE",
            "subject": "Mathematics",
            "grade": req.grade,
            "topic_slug": "algebra",
            "topic_title": "Algebra Basics",
            "tutor_name": "Ava",
            "lesson_stage": "INTRO",
            "summary": "Starting your math lesson.",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "lesson_notes": [],
            "metadata": {},
            "transcript": []
        },
        "archive": []
    }