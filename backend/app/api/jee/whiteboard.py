from fastapi import APIRouter

from pydantic import BaseModel

from app.services.jee.whiteboard_service import (
    generate_whiteboard
)

router = APIRouter()


class WhiteboardRequest(
    BaseModel
):
    question_text: str
    solution: str
    student_doubt: str


@router.post("/whiteboard")
def create_whiteboard(
    request: WhiteboardRequest
):

    board = generate_whiteboard(
        request.question_text,
        request.solution,
        request.student_doubt
    )

    return {
        "whiteboard": board
    }