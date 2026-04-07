from fastapi import APIRouter, HTTPException, Query

from ...models.session import SessionMessageRequest, StartSessionRequest
from ...services.session_service import session_service
from ...tutor_brain.runtime import tutor_engine

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("/start")
def start_session(request: StartSessionRequest):
    session = session_service.create_or_resume_session(request)
    tutor_engine.hydrate_session(session.session_id, session)
    return {
        "session": session_service.serialize_session(session, include_transcript=True),
        "archive": session_service.list_sessions(request.student_id, request.grade),
    }


@router.get("/history")
def session_history(
    student_id: str = Query(...),
    grade: int | None = Query(default=None),
):
    return {"sessions": session_service.list_sessions(student_id, grade)}


@router.get("/{session_id}")
def get_session(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session": session_service.serialize_session(session, include_transcript=True)}


@router.post("/message")
def send_message(request: SessionMessageRequest):
    session = session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    tutor_engine.hydrate_session(session.session_id, session)
    session_service.append_turn(session.session_id, "user", request.message)
    refreshed_session = session_service.get_session(session.session_id)
    response = tutor_engine.process(
        session.session_id,
        request.message,
        session_record=refreshed_session,
    )
    session_service.append_turn(session.session_id, "assistant", response)
    snapshot = tutor_engine.snapshot(session.session_id)
    session_service.update_lesson_snapshot(
        session.session_id,
        snapshot,
    )

    updated = session_service.get_session(session.session_id)
    return {
        "response": response,
        "whiteboard": snapshot.whiteboard if snapshot else None,
        "session": session_service.serialize_session(updated, include_transcript=True),
    }
