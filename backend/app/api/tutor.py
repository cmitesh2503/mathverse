from fastapi import APIRouter
from backend.app.api.models import TutorRequest
from backend.app.tutor_brain.tutor_engine import TutorEngine

router = APIRouter()

engine = TutorEngine()


@router.post("/ask")
def tutor_api(req: TutorRequest):

    print("🔥 /tutor/ask HIT")
    print("REQ:", req)

    state = engine._ensure_state(req.session_id)

    mode = req.mode
    input_data = req.input

    question = input_data.get("question")
    answer = input_data.get("answer")

    # ---------------------------
    # MODE ROUTING
    # ---------------------------

    if mode == "practice":
        state.active_problem = {"prompt": question}
        return engine._handle_answer(state, answer)

    elif mode == "doubt":
        return engine.handle_doubt(state, question)

    elif mode == "learn":
        return engine.handle_learn(state, question)

    elif mode == "ocr":
        return engine.handle_doubt(state, question)

    elif mode == "homework":
        return engine.handle_homework(state, question)

    return {"error": "Invalid mode"}