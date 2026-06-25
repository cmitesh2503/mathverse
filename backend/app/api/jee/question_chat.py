from fastapi import APIRouter
from pydantic import BaseModel

from app.services.jee.question_chat import (
    discuss_question
)

router = APIRouter()


class ChatRequest(BaseModel):
    question_id: str
    message: str
    

@router.post("/question-chat")
async def question_chat(
    request: ChatRequest
):
    return discuss_question(
        request.question_id,
        request.message
    )