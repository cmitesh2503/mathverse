from fastapi import APIRouter

from ...models.session import StartSessionRequest
from ...services.session_service import session_service


router = APIRouter()


@router.post("/start")
async def start_session(request: StartSessionRequest):
    session_record = session_service.create_or_resume_session(request)
    return {
        "session": session_service.serialize_session(session_record, include_transcript=True),
        "archive": session_service.list_sessions(session_record.student_id, session_record.grade),
    }
