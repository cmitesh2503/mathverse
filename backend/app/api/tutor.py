import os
from typing import Any
from datetime import timedelta
import re

from fastapi import APIRouter

from ..agents.diagnostic_agent import DiagnosticAgent
from ..agents.orchestrator import Orchestrator
from ..agents.proctor_agent import ProctorAgent
from ..agents.teacher_agent import TutorAgent
from ..models.session import StudentSession, utc_now
from ..services.rag_service import retrieve_context
from ..services.firebase_service import get_attempts, save_attempt
from .models import TutorRequest

router = APIRouter()
ATTEMPT_LOGGING_ENABLED = os.getenv("MATHVERSE_ENABLE_ATTEMPT_LOGGING", "").lower() in {"1", "true", "yes"}
CLASS_SESSION_MINUTES = 45

orchestrator = Orchestrator()
tutor_agent = TutorAgent()
diagnostic_agent = DiagnosticAgent()
proctor_agent = ProctorAgent()
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


def _action_text(action: dict[str, Any]) -> str:
    if not isinstance(action, dict):
        return ""

    action_name = str(action.get("action") or "").strip().lower()
    if action_name in {"clear", "clear_board", "erase", "reset_board"}:
        return ""

    text = (
        action.get("content")
        or action.get("text")
        or action.get("value")
        or action.get("message")
        or action.get("expression")
        or action.get("label")
        or ""
    )
    return str(text).strip()


def _steps_from_actions(whiteboard_actions: list[dict]) -> list[str]:
    steps: list[str] = []
    for action in whiteboard_actions:
        text = _action_text(action)
        if text:
            steps.append(text)
    return steps


def _steps_from_spoken_response(spoken_response: str, limit: int = 4) -> list[str]:
    if not isinstance(spoken_response, str):
        return []
    parts = [segment.strip() for segment in spoken_response.replace("\r", "\n").split("\n") if segment.strip()]
    if not parts:
        parts = [segment.strip() for segment in spoken_response.split(".") if segment.strip()]
    return parts[:limit]


def _is_greeting_line(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "welcome",
            "hello",
            "good morning",
            "good evening",
            "welcome back",
        )
    )


def _is_symbolic_math(text: str) -> bool:
    value = str(text or "").strip()
    lowered = value.lower()
    if not value:
        return False

    keyword_hits = (
        "subset",
        "superset",
        "union",
        "intersection",
        "cartesian",
        "roster",
        "set-builder",
        "domain",
        "range",
    )
    if any(keyword in lowered for keyword in keyword_hits):
        return True

    if any(token in value for token in ("=", "<=", ">=", "->", "=>", "^", "|", "{", "}")):
        return True

    if re.search(r"\b\d+\s*[-+*/]\s*\d+\b", value):
        return True

    if re.search(r"\(\s*[A-Za-z0-9]+\s*,\s*[A-Za-z0-9]+\s*\)", value):
        return True

    return False


def _is_equation_line(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    if "=" in value or "<=" in value or ">=" in value:
        return True
    if re.search(r"\b\d+\s*[-+*/]\s*\d+\b", value):
        return True
    if re.search(r"\b[A-Za-z]\s*\^", value):
        return True
    if re.search(r"\b[A-Za-z]\s*=\s*", value):
        return True
    return False


def _needs_problem_board(actions: list[dict[str, Any]]) -> bool:
    if not actions:
        return True

    has_equation_action = any(
        str(action.get("action", "")).strip().lower()
        in {"write_equation", "plot_curve", "draw_coordinate_axes", "draw_line", "draw_circle"}
        for action in actions
        if isinstance(action, dict)
    )
    if has_equation_action:
        return False

    equation_count = 0
    symbolic_count = 0
    prose_count = 0
    for action in actions:
        text = _action_text(action)
        if not text:
            continue
        if _is_equation_line(text):
            equation_count += 1
        elif _is_symbolic_math(text):
            symbolic_count += 1
        elif len(text.split()) >= 10:
            prose_count += 1

    if equation_count >= 1 and prose_count == 0:
        return False
    if symbolic_count >= 2:
        return False
    if symbolic_count == 1 and prose_count == 0:
        return False
    return True


def _extract_problem_candidates(rag_context: str, limit: int = 8) -> list[str]:
    if not isinstance(rag_context, str) or not rag_context.strip():
        return []

    candidates: list[str] = []
    seen: set[str] = set()
    lines = re.split(r"[\r\n]+", rag_context)
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not line:
            continue

        line = re.sub(r"^\s*(q(?:uestion)?|ex(?:ample)?)\s*[\d.:-]*\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\s+", " ", line).strip(" -:;")
        lowered = line.lower()
        if len(line) < 14 or len(line) > 220:
            continue
        if not (
            "?" in line
            or any(
                token in lowered
                for token in (
                    "solve",
                    "find",
                    "evaluate",
                    "prove",
                    "show",
                    "simplify",
                    "determine",
                    "calculate",
                )
            )
        ):
            continue

        key = lowered[:180]
        if key in seen:
            continue
        seen.add(key)
        candidates.append(line)
        if len(candidates) >= limit:
            break

    return candidates


def _generate_similar_problem(problem: str, seed: int) -> str:
    if not problem:
        return "Solve a similar variation for this concept."

    delta = (abs(int(seed)) % 3) + 1

    def _replace(match: re.Match) -> str:
        value = int(match.group(0))
        adjusted = value + delta if value >= 0 else value - delta
        return str(adjusted)

    mutated = re.sub(r"(?<![A-Za-z])\d+(?![A-Za-z])", _replace, problem)
    if mutated == problem:
        return f"Solve a similar PYQ-style variation of: {problem}"
    return mutated


def _pyq_problem_actions(topic: str, rag_context: str, variation: int = 0) -> list[dict[str, Any]]:
    sources = ["PYQ", "Study Material", "Generated from PYQ Pattern"]
    source_label = sources[variation % len(sources)]
    candidates = _extract_problem_candidates(rag_context)

    if candidates:
        base_problem = candidates[variation % len(candidates)]
    else:
        base_problem = f"Solve one step-by-step problem based on {topic or 'the current topic'}."

    if source_label == "Generated from PYQ Pattern":
        prompt = _generate_similar_problem(base_problem, variation + 1)
    elif source_label == "Study Material" and len(candidates) > 1:
        prompt = candidates[(variation + 1) % len(candidates)]
    else:
        prompt = base_problem

    return [
        {"action": "draw_text", "content": f"Source: {source_label}"},
        {"action": "draw_text", "content": f"Problem: {prompt}"},
        {"action": "draw_text", "content": "Step 1: Given -> Required"},
        {"action": "draw_text", "content": "Step 2: Pick rule from concept"},
        {"action": "draw_text", "content": "Step 3: Substitute and simplify"},
        {"action": "draw_text", "content": "Step 4: Final answer check"},
    ]


def _topic_problem_actions(topic: str, variation: int = 0, rag_context: str = "") -> list[dict[str, Any]]:
    lowered = (topic or "").lower()
    alt = variation % 2

    if "set notation" in lowered or "representations" in lowered:
        if alt == 0:
            return [
                {"action": "draw_text", "content": "Problem: Write B in roster form"},
                {"action": "write_equation", "content": "B = {x in N | 2 <= x <= 6}"},
                {"action": "write_equation", "content": "B = {2,3,4,5,6}"},
                {"action": "draw_text", "content": "Now compare with A = {1,2,3,4,5}"},
            ]
        return [
            {"action": "draw_text", "content": "Problem: Convert roster to set-builder"},
            {"action": "write_equation", "content": "A = {3,6,9,12}"},
            {"action": "write_equation", "content": "A = {x in N | x = 3n, 1 <= n <= 4}"},
        ]

    if "subset" in lowered or "types of sets" in lowered:
        return [
            {"action": "draw_text", "content": "Problem: Check subset and proper subset"},
            {"action": "write_equation", "content": "A = {1,2,3}, B = {1,2,3,4,5}"},
            {"action": "write_equation", "content": "A subseteq B  (every element of A is in B)"},
            {"action": "write_equation", "content": "A subset B because A != B"},
        ]

    if "operation" in lowered:
        return [
            {"action": "draw_text", "content": "Problem: Find union, intersection, differences"},
            {"action": "write_equation", "content": "A = {1,2,3,4}, B = {3,4,5,6}"},
            {"action": "write_equation", "content": "A union B = {1,2,3,4,5,6}"},
            {"action": "write_equation", "content": "A intersection B = {3,4}"},
            {"action": "write_equation", "content": "A - B = {1,2},  B - A = {5,6}"},
        ]

    if "venn" in lowered:
        return [
            {"action": "draw_text", "content": "Problem: Students liking Cricket (C) and Football (F)"},
            {"action": "write_equation", "content": "n(U)=40, n(C)=22, n(F)=18, n(C intersection F)=10"},
            {"action": "write_equation", "content": "Only C = 22 - 10 = 12"},
            {"action": "write_equation", "content": "Only F = 18 - 10 = 8"},
            {"action": "write_equation", "content": "Neither = 40 - (12+10+8) = 10"},
        ]

    if "ordered pair" in lowered or "cartesian" in lowered:
        return [
            {"action": "draw_text", "content": "Problem: Form Cartesian product and a relation"},
            {"action": "write_equation", "content": "A = {1,2}, B = {a,b}"},
            {"action": "write_equation", "content": "A x B = {(1,a),(1,b),(2,a),(2,b)}"},
            {"action": "write_equation", "content": "R = {(1,a),(2,b)} subseteq A x B"},
        ]

    if "relation" in lowered:
        return [
            {"action": "draw_text", "content": "Problem: Check relation properties"},
            {"action": "write_equation", "content": "A = {1,2,3}, R = {(1,1),(2,2),(3,3),(1,2),(2,1)}"},
            {"action": "write_equation", "content": "Reflexive: Yes (all (a,a) present)"},
            {"action": "write_equation", "content": "Symmetric: Yes ((1,2) and (2,1))"},
            {"action": "write_equation", "content": "Transitive: Check pairs to conclude"},
        ]

    return _pyq_problem_actions(topic=topic, rag_context=rag_context, variation=variation)


def _prepare_problem_whiteboard_actions(
    topic: str,
    actions: list[dict[str, Any]],
    variation: int,
    rag_context: str = "",
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action", "")).strip()
        if not action_name:
            continue
        text = _action_text(action)
        if text and _is_greeting_line(text):
            continue
        is_text_action = action_name.lower() in {"write", "write_text", "add_text", "text", "draw_text"}
        if text and is_text_action and len(text.split()) >= 14 and not _is_equation_line(text):
            continue
        if action_name.lower() in {"write", "write_text", "add_text", "text"} and not text:
            continue
        cleaned.append(action)

    if _needs_problem_board(cleaned):
        return _topic_problem_actions(topic, variation=variation, rag_context=rag_context)
    return cleaned


def _resolve_session_topic(session: StudentSession) -> str:
    if session.current_topic:
        return str(session.current_topic)
    if session.agenda and 0 <= session.current_topic_index < len(session.agenda):
        return str(session.agenda[session.current_topic_index])
    return str(session.chapter_name or "Current Topic")


def _ensure_board_header_actions(session: StudentSession, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chapter = str(session.chapter_name or "Current Chapter")
    topic = _resolve_session_topic(session)
    has_chapter = False
    has_topic = False
    for action in actions:
        text = _action_text(action).lower()
        if text.startswith("chapter:"):
            has_chapter = True
        if text.startswith("topic:"):
            has_topic = True

    header: list[dict[str, Any]] = []
    if not has_chapter:
        header.append({"action": "draw_text", "content": f"Chapter: {chapter}"})
    if not has_topic:
        header.append({"action": "draw_text", "content": f"Topic: {topic}"})
    if not header:
        return actions
    return [*header, *actions]


def _normalize_action(input_data: dict[str, Any]) -> str:
    return str(input_data.get("action") or "").strip().lower()


def _ensure_class_timer(session: StudentSession, action: str) -> None:
    if action == "start" or session.class_started_at is None:
        session.class_started_at = utc_now()
        session.class_duration_minutes = CLASS_SESSION_MINUTES


def _class_time_left_seconds(session: StudentSession) -> int:
    if session.class_started_at is None:
        return CLASS_SESSION_MINUTES * 60
    total_seconds = int(session.class_duration_minutes * 60)
    elapsed_seconds = int((utc_now() - session.class_started_at).total_seconds())
    return max(0, total_seconds - elapsed_seconds)


def _is_class_time_over(session: StudentSession) -> bool:
    if session.class_started_at is None:
        return False
    return utc_now() >= session.class_started_at + timedelta(minutes=session.class_duration_minutes)


def _class_expired_payload(session: StudentSession) -> dict:
    spoken_response = (
        f"Our {session.class_duration_minutes}-minute class session is complete for today. "
        "Great effort. Please review today's board notes and continue in a new class session."
    )
    return {
        "type": "chapter_complete",
        "chapter": session.current_topic,
        "topic": session.current_topic,
        "concept": session.current_topic,
        "explanation": spoken_response,
        "voice_text": spoken_response,
        "spoken_response": spoken_response,
        "steps": [
            f"Session complete: {session.class_duration_minutes} minutes",
            "Review board notes and homework",
            "Start a new class to continue",
        ],
        "whiteboard_actions": [
            {"action": "draw_text", "content": f"Session complete ({session.class_duration_minutes} minutes)"},
            {"action": "draw_text", "content": "Review today's notes and homework."},
        ],
        "whiteboard": {
            "title": session.current_topic or "Session complete",
            "subtitle": "Arvind Sir's smart blackboard",
            "chalk_lines": [
                f"Session complete: {session.class_duration_minutes} minutes",
                "Review today's notes and homework.",
            ],
            "actions": [
                {"action": "draw_text", "content": f"Session complete ({session.class_duration_minutes} minutes)"},
                {"action": "draw_text", "content": "Review today's notes and homework."},
            ],
        },
        "correct": None,
        "mistake_type": None,
        "diagnostic": None,
        "mock_test_score": session.mock_test_score,
        "correct_attempts": session.correct_attempts,
        "wrong_attempts": session.wrong_attempts,
        "questions_asked": session.questions_asked,
        "proctor": None,
        "next_action": "finish",
        "session_time_left_seconds": 0,
        "session_duration_seconds": int(session.class_duration_minutes * 60),
        "session_expired": True,
        "avatar_voice": {
            "style": "energetic",
            "pace": "short-punchy",
            "sync_to_whiteboard": True,
        },
        "avatar_stream": {
            "voice_chunks": [spoken_response],
            "steps": [
                f"Session complete: {session.class_duration_minutes} minutes",
                "Review today's notes and homework.",
            ],
            "pace": "short-punchy",
        },
    }


def _rag_context_for_session(session: StudentSession, exam_type: str) -> str:
    topic = (
        _resolve_session_topic(session)
        or session.chapter_name
    )
    query = (
        f"Grade {getattr(session, 'grade', 11)} "
        f"{str(exam_type or 'cbse').upper()} Mathematics "
        f"chapter {session.chapter_name or topic} "
        f"topic {topic} "
        "PYQ study material worked examples"
    ).strip()
    try:
        return retrieve_context(query=query, exam_type=exam_type, k=6)
    except Exception as error:
        print(f"Tutor RAG lookup failed ({type(error).__name__}): {error}")
        return ""


async def _handle_multi_agent_class(req: TutorRequest, input_data: dict[str, Any]) -> dict:
    session: StudentSession = orchestrator.get_or_create_session(req.session_id)
    route_context = dict(req.context or {})
    if "grade" not in route_context and input_data.get("grade") is not None:
        route_context["grade"] = input_data.get("grade")
    if "exam" not in route_context and req.get_exam():
        route_context["exam"] = req.get_exam()

    if route_context.get("grade") is not None:
        try:
            session.grade = int(route_context["grade"])
        except (TypeError, ValueError):
            pass
    session.exam = "jee" if str(route_context.get("exam", req.get_exam())).lower() == "jee" else "cbse"

    action = _normalize_action(input_data)
    _ensure_class_timer(session, action)
    if _is_class_time_over(session) and action != "start":
        return _class_expired_payload(session)

    session.current_topic = (
        input_data.get("topic")
        or input_data.get("chapter")
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

    route = await orchestrator.route_message(
        session.session_id,
        user_message,
        mode=req.mode,
        context=route_context,
    )
    session.current_topic = _resolve_session_topic(session)
    rag_context = _rag_context_for_session(session, session.exam)
    diagnostic_result = None
    nudge = None
    proctor_payload = None

    if route == "proctor_agent":
        proctor_payload = await proctor_agent.process_message(session, user_message)
        spoken_response = proctor_payload.get("spoken_response", "")
        whiteboard_actions = proctor_payload.get("whiteboard_actions", [])
    elif route == "diagnostic_agent":
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
            rag_context=rag_context,
        )
        spoken_response = tutor_payload.get("spoken_response", "")
        whiteboard_actions = tutor_payload.get("whiteboard_actions", [])
    else:
        tutor_payload = await tutor_agent.process_message(
            session,
            user_message,
            diagnostic_nudge=nudge,
            rag_context=rag_context,
        )
        spoken_response = tutor_payload.get("spoken_response", "")
        whiteboard_actions = tutor_payload.get("whiteboard_actions", [])

    whiteboard_actions = _prepare_problem_whiteboard_actions(
        topic=session.current_topic or session.chapter_name,
        actions=whiteboard_actions,
        variation=session.questions_asked,
        rag_context=rag_context,
    )
    session.questions_asked += 1
    whiteboard_actions = _ensure_board_header_actions(session, whiteboard_actions)
    steps = _steps_from_actions(whiteboard_actions)
    if not steps:
        fallback_actions = _topic_problem_actions(
            session.current_topic or session.chapter_name,
            variation=session.questions_asked,
            rag_context=rag_context,
        )
        whiteboard_actions = _ensure_board_header_actions(session, fallback_actions)
        steps = _steps_from_actions(whiteboard_actions)

    chapter_title = session.chapter_name or session.current_topic or "Current Chapter"
    topic_title = session.current_topic or chapter_title
    return {
        "type": "exam" if route == "proctor_agent" else ("teach" if route != "diagnostic_agent" else "evaluation"),
        "chapter": chapter_title,
        "topic": topic_title,
        "concept": topic_title,
        "explanation": spoken_response,
        "voice_text": spoken_response,
        "spoken_response": spoken_response,
        "steps": steps,
        "whiteboard_actions": whiteboard_actions,
        "whiteboard": {
            "title": f"{chapter_title} | {topic_title}",
            "subtitle": "Arvind Sir's smart blackboard",
            "chalk_lines": steps,
            "actions": whiteboard_actions,
        },
        "correct": diagnostic_result.get("is_correct") if diagnostic_result else None,
        "mistake_type": diagnostic_result.get("error_category") if diagnostic_result else None,
        "diagnostic": diagnostic_result,
        "mock_test_score": session.mock_test_score,
        "correct_attempts": session.correct_attempts,
        "wrong_attempts": session.wrong_attempts,
        "questions_asked": session.questions_asked,
        "proctor": proctor_payload,
        "next_action": "continue",
        "session_time_left_seconds": _class_time_left_seconds(session),
        "session_duration_seconds": int(session.class_duration_minutes * 60),
        "session_expired": False,
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

    try:
        mode = req.mode
        input_data = req.input

        if mode in {"class", "mock_test"}:
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
    except Exception as e:
        print(f"ERROR in /tutor/ask: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "type": type(e).__name__}


@router.get("/attempts/{student_id}")
def tutor_attempts(student_id: str, limit: int = 100):
    try:
        return {"attempts": get_attempts(student_id, limit)}
    except Exception as error:
        print("Attempt loading skipped:", error)
        return {"attempts": [], "error": "Attempt history is unavailable."}
