import os

from fastapi import APIRouter
from backend.app.api.models import TutorRequest
from backend.app.services.firebase_service import get_attempts, save_attempt
from backend.app.tutor_brain.tutor_engine import TutorEngine

router = APIRouter()
engine = TutorEngine()
ATTEMPT_LOGGING_ENABLED = os.getenv("MATHVERSE_ENABLE_ATTEMPT_LOGGING", "").lower() in {"1", "true", "yes"}


def _safe_save_attempt(payload: dict):
    if not ATTEMPT_LOGGING_ENABLED:
        return

    try:
        save_attempt(payload)
    except Exception as error:
        print("Attempt logging skipped:", error)


def _attempt_from_response(req: TutorRequest, state, response, question=None, answer=None) -> dict | None:
    if not isinstance(response, dict) or response.get("correct") is None:
        return None

    return {
        "session_id": req.session_id,
        "student_id": req.get_student_id(),
        "grade": getattr(state, "grade", None),
        "exam": req.get_exam(),
        "mode": req.mode,
        "chapter": response.get("chapter") or getattr(state, "chapter_label", None),
        "topic": response.get("topic") or getattr(state, "topic_title", None),
        "concept": response.get("concept") or getattr(state, "concept_title", None),
        "question": response.get("question") or question,
        "answer": answer,
        "correct": response.get("correct"),
        "mistake_type": response.get("mistake_type"),
        "difficulty": getattr(state, "difficulty", "easy"),
        "pattern": response.get("pattern"),
    }


@router.post("/ask")
def tutor_api(req: TutorRequest):

    print("🔥 /tutor/ask HIT")
    print("REQ:", req)

    state = engine._ensure_state(req.session_id)

    # ✅ NEW: extract exam safely
    exam = req.get_exam()
    state.exam = exam

    mode = req.mode
    input_data = req.input

    question = input_data.get("question")
    answer = input_data.get("answer")

    # ---------------------------
    # MODE ROUTING
    # ---------------------------

    response = None

    if mode == "practice":
        state.active_problem = {"prompt": question}
        response = engine._handle_answer(state, answer)

    elif mode == "doubt":
        response = engine.handle_doubt(state, question)

    elif mode == "learn":
        response = engine.handle_learn(state, input_data)

    elif mode == "class":
        response = engine.run_class(state, input_data)

    elif mode == "ocr":
        response = engine.handle_doubt(state, question)

    elif mode == "homework":
        response = engine.handle_homework(state, input_data)

    elif mode == "exam":
        response = engine.handle_exam(state, input_data)

    else:
        return {"error": "Invalid mode"}

    attempt = _attempt_from_response(req, state, response, question=question, answer=answer)
    if attempt:
        _safe_save_attempt(attempt)

    return response


@router.get("/attempts/{student_id}")
def tutor_attempts(student_id: str, limit: int = 100):
    try:
        return {"attempts": get_attempts(student_id, limit)}
    except Exception as error:
        print("Attempt loading skipped:", error)
        return {"attempts": [], "error": "Attempt history is unavailable."}
