from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional


# ✅ Request model (FIXES 422)
class PracticeRequest(BaseModel):
    session_id: str
    answer: Optional[str] = None
    grade: int = 10
    chapter: Optional[str] = None


router = APIRouter()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from ..tutor_brain.tutor_engine import TutorEngine

        _engine = TutorEngine()
    return _engine

# ✅ Track last question
last_question_id = None


# 🔥 ANSWER API (FIXED)
@router.post("/answer")
def submit_answer(req: PracticeRequest):

    print("🔥 API HIT /answer")
    print("REQ:", req)

    try:
        engine = _get_engine()
        state = engine._ensure_state(req.session_id)

        # ✅ Safety check
        if not req.answer:
            return {"response": "Answer missing"}

        result = engine._handle_answer(state, req.answer)

        
        return result
        

    except Exception as e:
        print("❌ ERROR:", e)
        return {
            "response": "Server error"
        }


# 🔥 NEXT QUESTION API (FIXED)
@router.post("/next")
def next_question(req: PracticeRequest):

    print("🔥 API HIT /next")

    try:
        engine = _get_engine()
        state = engine._ensure_state(req.session_id)

        from ..services.cbse_exercises import load_chapter_pdf_exercises

        chapter_title = req.chapter or getattr(state, "chapter_title", "") or getattr(state, "topic", "")
        problems = load_chapter_pdf_exercises(
            req.grade or getattr(state, "grade", 10),
            getattr(state, "chapter_index", 1),
            chapter_title,
        )
        if not problems:
            return {"question": "No Knowledge Factory practice question is available for this chapter."}

        question = problems[state.class_problem_cursor % len(problems)]
        state.class_problem_cursor += 1
        state.active_problem = question
        return {"question": question.get("prompt"), "source": "knowledge_factory"}

    except Exception as e:
        print("❌ ERROR:", e)
        return {
            "question": "Error loading question"
        }
        
@router.post("/explain")
def explain_answer(req: PracticeRequest):

    engine = _get_engine()
    state = engine._ensure_state(req.session_id)
    problem = state.active_problem

    if not problem:
        return {"explanation": "No active problem"}

    explanation = engine.generate_explanation(
        problem.get("prompt"),
        req.answer
    )

    return {
        "explanation": explanation
    }
