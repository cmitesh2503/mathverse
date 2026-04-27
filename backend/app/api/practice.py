from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import random

from backend.app.tutor_brain.tutor_engine import TutorEngine
from backend.app.data.question_loader import QUESTIONS


# ✅ Request model (FIXES 422)
class PracticeRequest(BaseModel):
    session_id: str
    answer: Optional[str] = None


router = APIRouter()

engine = TutorEngine()

# ✅ Track last question
last_question_id = None


# ✅ Question selector (no repetition)
def select_question(topic="quadratics", difficulty="easy"):
    global last_question_id

    filtered = [
        q for q in QUESTIONS
        if q.get("topic") == topic and q.get("difficulty") == difficulty
    ]

    if not filtered:
        return random.choice(QUESTIONS)

    available = [q for q in filtered if q.get("id") != last_question_id]

    if not available:
        available = filtered

    q = random.choice(available)
    last_question_id = q.get("id")

    return q


# 🔥 ANSWER API (FIXED)
@router.post("/answer")
def submit_answer(req: PracticeRequest):

    print("🔥 API HIT /answer")
    print("REQ:", req)

    try:
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
        state = engine._ensure_state(req.session_id)

        # ✅ NOW SAFE
        difficulty = engine.get_difficulty(state)

        q = select_question(difficulty=difficulty)

        state.active_problem = q

        print("DIFFICULTY:", difficulty)
        print("QUESTION:", q.get("prompt"))

        return {
            "question": q.get("prompt")
        }

    except Exception as e:
        print("❌ ERROR:", e)
        return {
            "question": "Error loading question"
        }
        
@router.post("/explain")
def explain_answer(req: PracticeRequest):

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