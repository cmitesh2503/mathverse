from fastapi import APIRouter, HTTPException

from ...models.session import StartSessionRequest
from ...services.session_service import session_service
from ...core import config


router = APIRouter()


@router.post("/start")
async def start_session(request: StartSessionRequest):
    session_record = session_service.create_or_resume_session(request)
    return {
        "session": session_service.serialize_session(session_record, include_transcript=True),
        "archive": session_service.list_sessions(session_record.student_id, session_record.grade),
    }


@router.get("/curriculum/{grade}")
async def get_curriculum(grade: int, board: str = "CBSE", subject: str = "Mathematics"):
    from ...tutor_brain.curriculum import get_grade_curriculum

    if subject.strip().lower() != "mathematics":
        raise HTTPException(
            status_code=404,
            detail="Only the Knowledge Factory Mathematics package is available.",
        )

    payload = get_grade_curriculum(grade, board.lower())
    if config.APP_ENV.lower() in {"development", "dev", "test"}:
        payload = {**payload, "source": "knowledge-factory-firestore"}
    return payload
