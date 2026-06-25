from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from app.services.jee.parser import parse_response
from app.services.jee.question_repository import save_question

from app.services.jee.question_solver import (
    solve_question_from_image
)

router = APIRouter()


@router.post("/solve-question")
async def solve_question(
    file: UploadFile = File(...)
):

    image_bytes = await file.read()

    result = solve_question_from_image(
        image_bytes
    )

    parsed = parse_response(result)

    question_id = save_question(
        parsed["question"],
        parsed["chapter"],
        parsed["answer"],
        parsed["solution"]
    )

    print("="*60)
    print("PARSED RESPONSE")
    print(parsed)
    print("="*60)

    return {
        "question_id": question_id,
        "question": parsed["question"],
        "answer": parsed["answer"],
        "solution": parsed["solution"],
        "chapter": parsed["chapter"]
    }
    print(parsed)