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
from ..services.cbse_exercises import build_exercise_solution
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


def _spoken_from_steps(
    spoken_response: str,
    steps: list[str],
    topic_title: str,
) -> str:
    spoken = str(spoken_response or "").strip()
    lowered = spoken.lower()
    is_placeholder = bool(
        spoken
        and (
            "finished the current board steps" in lowered
            or "click next when you are ready" in lowered
            or "ready for the next explanation" in lowered
        )
    )
    compact_steps = [str(step).strip() for step in steps if str(step).strip()]
    filtered = [
        line
        for line in compact_steps
        if not line.lower().startswith(("chapter:", "topic:", "source:"))
    ]
    ordered_step_lines = [
        line
        for line in filtered
        if line.lower().startswith("step ")
        or line.lower().startswith("problem:")
        or line.lower().startswith("final answer:")
        or line.lower().startswith("diagram:")
    ]
    narrated_steps = ordered_step_lines if ordered_step_lines else filtered

    if spoken and not is_placeholder:
        spoken_step_count = len(re.findall(r"\bstep\s*\d+\b", lowered))
        if narrated_steps and spoken_step_count < min(4, len(narrated_steps)):
            return (
                f"{spoken} "
                f"Now I will explain each board step with reason. {' '.join(narrated_steps[:10])}"
            )
        return spoken
    if compact_steps:
        if narrated_steps:
            return (
                f"Let us continue {topic_title} step by step. "
                + " ".join(narrated_steps[:10])
            )
        return " ".join(compact_steps[:4])
    return (
        f"We finished the current board steps for {topic_title}. "
        "Click Next when you are ready for the next explanation."
    )


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

    text_items = [_action_text(action) for action in actions if isinstance(action, dict)]
    text_items = [item for item in text_items if item]
    step_count = sum(1 for item in text_items if re.match(r"(?i)^step\s*\d+", item))
    has_final_answer = any(item.lower().startswith("final answer") for item in text_items)
    if step_count >= 2 or has_final_answer:
        return False

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
        if lowered.startswith("this theorem can be proved") or lowered.startswith("proof"):
            continue
        if lowered.endswith(("such", "therefore", "hence")):
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
    lowered_context = (rag_context or "").lower()
    if "ncert" in lowered_context or "cbse" in lowered_context:
        sources = ["NCERT Example", "NCERT Exercise", "Similar NCERT Practice"]
    else:
        sources = ["PYQ", "Study Material", "Generated from PYQ Pattern"]
    source_label = sources[variation % len(sources)]
    candidates = _extract_problem_candidates(rag_context)
    topic_candidates = _best_topic_candidates(candidates, topic=topic, chapter=topic)

    if topic_candidates:
        base_problem = topic_candidates[variation % len(topic_candidates)]
    else:
        base_problem = f"Solve one step-by-step problem based on {topic or 'the current topic'}."

    if source_label in {"Generated from PYQ Pattern", "Similar NCERT Practice"}:
        prompt = _generate_similar_problem(base_problem, variation + 1)
    elif source_label in {"Study Material", "NCERT Exercise"} and len(topic_candidates) > 1:
        prompt = topic_candidates[(variation + 1) % len(topic_candidates)]
    else:
        prompt = base_problem

    solved = build_exercise_solution(
        {
            "chapter_title": topic or "Mathematics",
            "exercise": source_label,
            "number": str(variation + 1),
            "prompt": prompt,
        }
    )
    solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
    answer = str(solved.get("answer") or "").strip()

    actions: list[dict[str, Any]] = [
        {"action": "draw_text", "content": f"Problem: {prompt}"},
        {"action": "draw_text", "content": f"Source: {source_label}"},
    ]
    for index, step in enumerate(solved_steps[:8], start=1):
        actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
    if answer:
        actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
    return actions


def _topic_problem_actions(topic: str, variation: int = 0, rag_context: str = "") -> list[dict[str, Any]]:
    lowered = (topic or "").lower()

    if "euclid" in lowered or "division lemma" in lowered:
        divisors = [5, 7, 8, 9, 11, 13, 14, 15]
        divisor = divisors[variation % len(divisors)]
        quotient = 6 + (variation % 11)
        remainder = 1 + ((variation * 3) % max(1, divisor - 1))
        dividend = divisor * quotient + remainder
        prompt = (
            f"Using Euclid's division lemma, write {dividend} in the form {divisor}q + r. "
            "What are q and r?"
        )
        solved = build_exercise_solution(
            {
                "chapter_title": "Real Numbers",
                "exercise": "Euclid's Division Lemma",
                "number": str(variation + 1),
                "prompt": prompt,
            }
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()
        actions: list[dict[str, Any]] = [
            {"action": "draw_text", "content": f"Problem: {prompt}"},
            {"action": "draw_text", "content": "Source: Chapter Exercise"},
            {"action": "draw_text", "content": "Diagram: a = bq + r with quotient part and remainder part."},
        ]
        for index, step in enumerate(solved_steps[:8], start=1):
            actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
        if answer:
            actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
        return actions

    if "hcf" in lowered or "lcm" in lowered or "euclid algorithm" in lowered:
        hcf_base = 2 + (variation % 9)
        hcf = 3 + (variation % 7)
        first = hcf * (2 * hcf_base + 5)
        second = hcf * (hcf_base + 4)
        if first == second:
            second += hcf
        prompt = f"Find HCF of {first} and {second} using Euclid's algorithm."
        solved = build_exercise_solution(
            {
                "chapter_title": "Real Numbers",
                "exercise": "Revisiting HCF and LCM",
                "number": str(variation + 1),
                "prompt": prompt,
            }
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()
        actions: list[dict[str, Any]] = [
            {"action": "draw_text", "content": f"Problem: {prompt}"},
            {"action": "draw_text", "content": "Source: Chapter Exercise"},
            {"action": "draw_text", "content": "Diagram: Division chain with decreasing remainders."},
        ]
        for index, step in enumerate(solved_steps[:8], start=1):
            actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
        if answer:
            actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
        return actions

    if "decimal expansion" in lowered:
        if variation % 2 == 0:
            pow2 = 3 + (variation % 4)
            pow5 = 1 + (variation % 3)
            denominator = (2 ** pow2) * (5 ** pow5)
            numerator = 3 + (variation % 17)
        else:
            denominator = (2 ** (2 + (variation % 3))) * (3 + (variation % 5))
            numerator = 5 + ((variation * 2) % 19)
        fraction = f"{numerator}/{denominator}"
        prompt = f"State whether {fraction} has a terminating decimal expansion or a non-terminating repeating decimal expansion."
        solved = build_exercise_solution(
            {
                "chapter_title": "Real Numbers",
                "exercise": "Decimal Expansions",
                "number": str(variation + 1),
                "prompt": prompt,
            }
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()
        actions: list[dict[str, Any]] = [
            {"action": "draw_text", "content": f"Problem: {prompt}"},
            {"action": "draw_text", "content": "Source: Chapter Exercise"},
            {"action": "draw_text", "content": "Diagram: Prime factors of denominator determine decimal type."},
        ]
        for index, step in enumerate(solved_steps[:8], start=1):
            actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
        if answer:
            actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
        return actions

    if "irrational" in lowered:
        radicals = [2, 3, 5, 7, 11]
        radicand = radicals[variation % len(radicals)]
        coefficient = 2 + (variation % 9)
        constant = 3 + ((variation * 2) % 11)
        prompt = f"Show that {constant} + {coefficient}sqrt({radicand}) is irrational."
        solved = build_exercise_solution(
            {
                "chapter_title": "Real Numbers",
                "exercise": "Irrational Numbers",
                "number": str(variation + 1),
                "prompt": prompt,
            }
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()
        actions: list[dict[str, Any]] = [
            {"action": "draw_text", "content": f"Problem: {prompt}"},
            {"action": "draw_text", "content": "Source: Chapter Exercise"},
            {"action": "draw_text", "content": "Diagram: Contradiction flow -> assumption leads to impossible result."},
        ]
        for index, step in enumerate(solved_steps[:8], start=1):
            actions.append({"action": "draw_text", "content": f"Step {index}: {step}"})
        if answer:
            actions.append({"action": "draw_text", "content": f"Final answer: {answer}"})
        return actions

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
        if text and is_text_action and len(text.split()) >= 28 and not _is_equation_line(text):
            structured = re.match(r"(?i)^(step\s*\d+|problem:|final answer:|source:|chapter:|topic:)", text)
            if not structured:
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


def _ensure_board_header_actions(
    session: StudentSession,
    actions: list[dict[str, Any]],
    *,
    include_headers: bool = True,
) -> list[dict[str, Any]]:
    if not include_headers:
        return actions

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


def _class_user_message(input_data: dict[str, Any], action: str) -> str:
    if input_data.get("answer"):
        return f"My final answer is {input_data['answer']}"
    if input_data.get("question"):
        return str(input_data.get("question"))
    if input_data.get("topic"):
        return str(input_data.get("topic"))

    if action == "start":
        return "start"
    if action == "next":
        return "next_step"
    if action in {"continue", "repeat"}:
        return "next_step"
    if action in {"next_topic", "next_chapter", "skip_topic", "skip_chapter"}:
        return "next_topic"
    if action in {"homework", "finish", "end"}:
        return "homework"
    if action in {"help", "unable", "not_able"}:
        return "help"
    if action:
        return action
    return "ready"


def _topic_keywords(value: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z]{4,}", str(value or "").lower())
    stop_words = {"chapter", "grade", "class", "mathematics", "math", "topic", "concept", "exercise"}
    unique: list[str] = []
    for token in tokens:
        if token in stop_words:
            continue
        if token not in unique:
            unique.append(token)
    return unique[:6]


def _topic_match_score(text: str, *, topic: str, chapter: str) -> int:
    lowered = str(text or "").lower()
    score = 0
    for keyword in _topic_keywords(topic):
        if keyword in lowered:
            score += 3
    for keyword in _topic_keywords(chapter):
        if keyword in lowered:
            score += 1
    return score


def _best_topic_candidates(candidates: list[str], *, topic: str, chapter: str) -> list[str]:
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        scored.append((_topic_match_score(candidate, topic=topic, chapter=chapter), candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for score, candidate in scored if score > 0]


def _scope_rag_context_to_chapter(raw_context: str, chapter: str, topic: str) -> str:
    if not isinstance(raw_context, str) or not raw_context.strip():
        return ""

    blocks = [block.strip() for block in raw_context.split("\n\n") if block.strip()]
    if not blocks:
        return raw_context

    keywords = _topic_keywords(chapter) + _topic_keywords(topic)
    if not keywords:
        return "\n\n".join(blocks[:6])

    scoped: list[str] = []
    for block in blocks:
        lowered = block.lower()
        if any(keyword in lowered for keyword in keywords):
            scoped.append(block)

    if scoped:
        return "\n\n".join(scoped[:6])
    return "\n\n".join(blocks[:6])


def _widget_to_actions(widget: Any) -> list[dict[str, Any]]:
    if not isinstance(widget, dict):
        return []

    widget_type = str(widget.get("type") or "").strip().lower()
    props = widget.get("props") if isinstance(widget.get("props"), dict) else {}

    if widget_type == "graph":
        equations = props.get("equations") if isinstance(props.get("equations"), list) else []
        preview = ", ".join(str(eq).strip() for eq in equations if str(eq).strip()) or "relevant curve"
        return [{"action": "draw_text", "content": f"Diagram: Plot the graph for {preview}."}]

    if widget_type == "number_line":
        points = props.get("points") if isinstance(props.get("points"), list) else []
        preview = ", ".join(str(point).strip() for point in points if str(point).strip()) or "key values"
        return [{"action": "draw_text", "content": f"Diagram: Draw a number line and mark {preview}."}]

    if widget_type == "venn":
        sets = props.get("sets") if isinstance(props.get("sets"), list) else []
        labels = []
        for item in sets:
            if isinstance(item, dict) and str(item.get("name") or "").strip():
                labels.append(str(item["name"]).strip())
        joined = ", ".join(labels) if labels else "the required sets"
        return [{"action": "draw_text", "content": f"Diagram: Draw a Venn diagram for {joined} and mark common elements."}]

    return []


def _chapter_transition_actions(transition: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    from_chapter = str(transition.get("from_chapter") or "Current chapter").strip()
    to_chapter = str(transition.get("to_chapter") or "Next chapter").strip()
    first_topic = str(transition.get("first_topic") or "").strip()
    raw_topics = transition.get("topics") if isinstance(transition.get("topics"), list) else []
    topics = [str(item).strip() for item in raw_topics if str(item).strip()][:8]

    spoken = (
        f"Excellent work. We completed {from_chapter}. "
        f"Now we are starting a new chapter: {to_chapter}. "
    )
    if topics:
        spoken += "In this chapter we will cover: " + ", ".join(topics) + ". "
    if first_topic:
        spoken += f"First topic is {first_topic}."

    actions: list[dict[str, Any]] = [
        {"action": "draw_text", "content": f"Chapter complete: {from_chapter}"},
        {"action": "draw_text", "content": f"Starting new chapter: {to_chapter}"},
    ]
    if topics:
        actions.append({"action": "draw_text", "content": "Topic list:"})
        for index, topic in enumerate(topics, start=1):
            actions.append({"action": "draw_text", "content": f"{index}. {topic}"})
    if first_topic:
        actions.append({"action": "draw_text", "content": f"Now starting: {first_topic}"})

    return spoken.strip(), actions


def _exercise_nudge_from_rag(rag_context: str, variation: int) -> str | None:
    candidates = _extract_problem_candidates(rag_context)
    if not candidates:
        return None
    selected = candidates[variation % len(candidates)]
    return (
        "SYSTEM INSTRUCTION: Solve at least one exercise question fully on the whiteboard now. "
        "Use this question if relevant: "
        f"{selected}"
    )


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
            "style": "calm",
            "pace": "slow-paused",
            "sync_to_whiteboard": True,
            "pause_ms": 520,
        },
        "avatar_stream": {
            "voice_chunks": [spoken_response],
            "steps": [
                f"Session complete: {session.class_duration_minutes} minutes",
                "Review today's notes and homework.",
            ],
            "pace": "slow-paused",
            "pause_ms": 520,
        },
    }


def _rag_context_for_session(session: StudentSession, exam_type: str) -> str:
    topic = (
        _resolve_session_topic(session)
        or session.chapter_name
    )
    chapter = session.chapter_name or topic
    normalized_exam = "jee" if str(exam_type or "").lower() == "jee" else "cbse"
    source_hint = (
        "JEE PYQ patterns, solved examples, and problem solving strategies"
        if normalized_exam == "jee"
        else "NCERT textbook concept explanations, worked examples, and exercise questions"
    )
    query = (
        f"Grade {getattr(session, 'grade', 10)} "
        f"{normalized_exam.upper()} Mathematics "
        f"ONLY chapter {chapter}. "
        f"Current topic {topic}. "
        f"{source_hint}. Ignore unrelated chapters."
    ).strip()
    try:
        raw_context = retrieve_context(query=query, exam_type=normalized_exam, k=8)
        return _scope_rag_context_to_chapter(raw_context, chapter=chapter, topic=topic)
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
    turn_index = int(getattr(session, "class_problem_cursor", 0))
    _ensure_class_timer(session, action)
    if _is_class_time_over(session) and action != "start":
        return _class_expired_payload(session)

    session.current_topic = (
        input_data.get("topic")
        or input_data.get("chapter")
        or session.current_topic
        or ("JEE Mathematics" if session.exam == "jee" else "CBSE Mathematics")
    )
    session.active_phase = "practice" if input_data.get("answer") else "teaching"

    if input_data.get("question"):
        session.current_problem = {"prompt": input_data["question"]}

    user_message = _class_user_message(input_data, action)

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
    tutor_payload: dict[str, Any] | None = None
    transition_spoken_prefix = ""
    transition_actions: list[dict[str, Any]] = []
    continuation_nudge = None
    if action in {"next", "continue", "repeat"}:
        continuation_nudge = (
            "SYSTEM INSTRUCTION: Student clicked Next. Continue the same topic from the next sub-step. "
            "Do not restart the chapter intro and do not repeat the same solved problem."
        )

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
        exercise_nudge = _exercise_nudge_from_rag(rag_context, turn_index)
        nudge = "\n".join(part for part in [nudge, continuation_nudge, exercise_nudge] if part)
        tutor_payload = await tutor_agent.process_message(
            session,
            user_message,
            diagnostic_nudge=nudge,
            rag_context=rag_context,
        )
        spoken_response = tutor_payload.get("spoken_response", "")
        whiteboard_actions = tutor_payload.get("whiteboard_actions", [])
    else:
        exercise_nudge = _exercise_nudge_from_rag(rag_context, turn_index)
        nudge = "\n".join(part for part in [continuation_nudge, exercise_nudge] if part)
        tutor_payload = await tutor_agent.process_message(
            session,
            user_message,
            diagnostic_nudge=nudge,
            rag_context=rag_context,
        )
        spoken_response = tutor_payload.get("spoken_response", "")
        whiteboard_actions = tutor_payload.get("whiteboard_actions", [])

    if route != "proctor_agent" and tutor_payload:
        whiteboard_actions = [*whiteboard_actions, *_widget_to_actions(tutor_payload.get("widget"))]

    if route != "proctor_agent" and tutor_payload and tutor_payload.get("advance_topic"):
        next_topic = orchestrator._advance_to_next_topic(session)
        whiteboard_actions = [
            *whiteboard_actions,
            {"action": "draw_text", "content": f"Topic complete. Next topic: {next_topic}"},
        ]

    if route != "proctor_agent" and isinstance(session.chapter_transition, dict):
        transition_spoken_prefix, transition_actions = _chapter_transition_actions(session.chapter_transition)
        session.chapter_transition = None

    if transition_spoken_prefix:
        spoken_response = f"{transition_spoken_prefix} {spoken_response}".strip()

    whiteboard_actions = _prepare_problem_whiteboard_actions(
        topic=session.current_topic or session.chapter_name,
        actions=whiteboard_actions,
        variation=turn_index,
        rag_context=rag_context,
    )
    if transition_actions:
        whiteboard_actions = [*transition_actions, *whiteboard_actions]
    include_headers = action in {"start", "next_topic", "next_chapter", "skip_topic", "skip_chapter"} or turn_index == 0
    whiteboard_actions = _ensure_board_header_actions(session, whiteboard_actions, include_headers=include_headers)
    steps = _steps_from_actions(whiteboard_actions)
    if not steps:
        fallback_actions = _topic_problem_actions(
            session.current_topic or session.chapter_name,
            variation=turn_index,
            rag_context=rag_context,
        )
        whiteboard_actions = _ensure_board_header_actions(session, fallback_actions, include_headers=include_headers)
        steps = _steps_from_actions(whiteboard_actions)
    session.class_problem_cursor = turn_index + 1
    session.questions_asked = int(getattr(session, "questions_asked", 0)) + 1

    chapter_title = session.chapter_name or session.current_topic or "Current Chapter"
    topic_title = session.current_topic or chapter_title
    spoken_response = _spoken_from_steps(spoken_response, steps, topic_title)
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
            "style": "calm",
            "pace": "slow-paused",
            "sync_to_whiteboard": True,
            "pause_ms": 520,
        },
        "avatar_stream": {
            "voice_chunks": [spoken_response] if spoken_response else [],
            "steps": steps,
            "pace": "slow-paused",
            "pause_ms": 520,
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
