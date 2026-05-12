import os
from typing import Any

from fastapi import APIRouter

from ..agents.diagnostic_agent import DiagnosticAgent
from ..agents.orchestrator import Orchestrator
from ..agents.teacher_agent import TutorAgent
from ..models.session import StudentSession
from ..services.firebase_service import get_attempts, save_attempt
from .models import TutorRequest

router = APIRouter()
ATTEMPT_LOGGING_ENABLED = os.getenv("MATHVERSE_ENABLE_ATTEMPT_LOGGING", "").lower() in {"1", "true", "yes"}

orchestrator = Orchestrator()
tutor_agent = TutorAgent()
diagnostic_agent = DiagnosticAgent()
_legacy_engine = None


def _get_legacy_engine():
    global _legacy_engine
    if _legacy_engine is None:
        from ..tutor_brain.tutor_engine import TutorEngine

        _legacy_engine = TutorEngine()
    return _legacy_engine


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


def _steps_from_actions(whiteboard_actions: list[dict]) -> list[str]:
    return [
        action.get("content") or action.get("action", "").replace("_", " ")
        for action in whiteboard_actions
        if isinstance(action, dict)
    ]


async def _handle_multi_agent_class(req: TutorRequest, input_data: dict[str, Any]) -> dict:
    session: StudentSession = orchestrator.get_or_create_session(req.session_id)
    session.current_topic = (
        input_data.get("topic")
        or input_data.get("chapter")
        or input_data.get("question")
        or session.current_topic
        or "JEE Mathematics"
    )
    session.active_phase = "practice" if input_data.get("answer") else "teaching"

    if input_data.get("question"):
        session.current_problem = {"prompt": input_data["question"]}

    user_message = (
        f"My final answer is {input_data['answer']}"
        if input_data.get("answer")
        else input_data.get("question")
        or input_data.get("topic")
        or input_data.get("action")
        or "ready"
    )

    route = await orchestrator.route_message(session.session_id, user_message)
    diagnostic_result = None
    nudge = None

    if route == "diagnostic_agent":
        diagnostic_result = await diagnostic_agent.evaluate_answer(
            session,
            input_data.get("answer") or user_message,
            correct_answer="42",
        )
        nudge = diagnostic_result.get("hidden_nudge")

    tutor_payload = await tutor_agent.process_message(
        session,
        user_message,
        diagnostic_nudge=nudge,
    )
    spoken_response = tutor_payload.get("spoken_response", "")
    whiteboard_actions = tutor_payload.get("whiteboard_actions", [])
    steps = _steps_from_actions(whiteboard_actions)

    return {
        "type": "teach" if route != "diagnostic_agent" else "evaluation",
        "chapter": session.current_topic,
        "topic": session.current_topic,
        "concept": session.current_topic,
        "explanation": spoken_response,
        "voice_text": spoken_response,
        "spoken_response": spoken_response,
        "steps": steps,
        "whiteboard_actions": whiteboard_actions,
        "whiteboard": {
            "title": session.current_topic or "Smart Blackboard",
            "subtitle": "Arvind Sir's smart blackboard",
            "chalk_lines": steps,
            "actions": whiteboard_actions,
        },
        "correct": diagnostic_result.get("is_correct") if diagnostic_result else None,
        "mistake_type": diagnostic_result.get("error_category") if diagnostic_result else None,
        "diagnostic": diagnostic_result,
        "next_action": "next",
        "avatar_voice": {
            "style": "energetic",
            "pace": "short-punchy",
            "sync_to_whiteboard": True,
        },
        "avatar_stream": {
            "voice_chunks": [spoken_response] if spoken_response else [],
            "steps": steps,
            "pace": "short-punchy",
        },
    }


@router.post("/ask")
async def tutor_api(req: TutorRequest):
    print("POST /tutor/ask")
    print("REQ:", req)

    mode = req.mode
    input_data = req.input

    if mode == "class":
        return await _handle_multi_agent_class(req, input_data)

    engine = _get_legacy_engine()
    state = engine._ensure_state(req.session_id)
    state.exam = req.get_exam()

    question = input_data.get("question")
    answer = input_data.get("answer")

    response = None

    if mode == "practice":
        state.active_problem = {"prompt": question}
        response = engine._handle_answer(state, answer)

    elif mode == "doubt":
        response = engine.handle_doubt(state, question)

    elif mode == "learn":
        response = engine.handle_learn(state, input_data)

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
