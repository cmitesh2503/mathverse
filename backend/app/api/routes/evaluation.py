from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agents.chapter_test_agent import chapter_test_agent
from ...services.session_service import session_service


router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class ChapterTestSubmission(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


@router.get("/chapter-test/{session_id}")
def get_chapter_test(session_id: str, refresh: bool = False):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return chapter_test_agent.get_or_create(session, refresh=refresh)


@router.post("/chapter-test/{session_id}/submit")
def submit_chapter_test(session_id: str, submission: ChapterTestSubmission):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        result = chapter_test_agent.evaluate(session_id, submission.answers)
    except KeyError:
        chapter_test_agent.get_or_create(session)
        result = chapter_test_agent.evaluate(session_id, submission.answers)

    return {"result": result}
