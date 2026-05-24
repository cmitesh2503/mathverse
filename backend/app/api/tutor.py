import os
import base64
from typing import Any
from datetime import timedelta
import re

from fastapi import APIRouter

from ..agents.diagnostic_agent import DiagnosticAgent
from ..agents.orchestrator import Orchestrator
from ..agents.proctor_agent import ProctorAgent
from ..agents.teacher_agent import TutorAgent
from ..models.session import StudentSession, utc_now
from ..services.cbse_exercises import (
    build_exercise_solution,
    get_pdf_chapter_number,
    load_chapter_pdf_exercises,
)
from ..services.rag_service import retrieve_context
from ..services.firebase_service import get_attempts, save_attempt
from ..services.ai_gateway import generate_audio
from ..services.math_formatter import (
    convert_text_to_display_symbols,
    convert_display_symbols_to_speech,
    convert_text_to_speech,
)
from ..tutor_brain.curriculum import get_grade_curriculum
from .models import TutorRequest

router = APIRouter()
ATTEMPT_LOGGING_ENABLED = os.getenv("MATHVERSE_ENABLE_ATTEMPT_LOGGING", "").lower() in {"1", "true", "yes"}
TTS_ENABLED = os.getenv("MATHVERSE_ENABLE_TTS", "").lower() in {"1", "true", "yes"}
CLASS_SESSION_MINUTES = 45

orchestrator = Orchestrator()
tutor_agent = TutorAgent()
diagnostic_agent = DiagnosticAgent()
proctor_agent = ProctorAgent()
_legacy_engine = None
_RAG_CONTEXT_CACHE: dict[tuple[int, str, str, str], str] = {}


def _sanitize_for_speech(text: str) -> str:
    """
    Convert text and symbols to natural speech.
    Uses math_formatter for consistent symbol handling.
    """
    if not text:
        return text
    # Use the new comprehensive formatter
    return convert_text_to_speech(text)


def _format_for_display(text: str) -> str:
    """
    Convert text-based math notation to proper display symbols.
    Example: "sqrt(x)" → "√(x)"
    """
    if not text:
        return text
    return convert_text_to_display_symbols(text)


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


def _normalize_teaching_language(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized in {"hi", "hindi", "hi-in"}:
        return "hi-IN"
    if normalized in {"gu", "gujarati", "gu-in"}:
        return "gu-IN"
    return "en-IN"


def _spoken_from_steps(
    spoken_response: str,
    steps: list[str],
    topic_title: str,
    teaching_language: str = "en-IN",
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
    problem_no_line = next(
        (
            line
            for line in compact_steps
            if line.lower().startswith("problem no:")
        ),
        "",
    )
    problem_line = next(
        (
            line
            for line in compact_steps
            if line.lower().startswith("problem statement:")
        ),
        "",
    )
    figure_line = next(
        (
            line
            for line in compact_steps
            if line.lower().startswith("figure") or line.lower().startswith("diagram")
        ),
        "",
    )
    ordered_step_lines = [
        line
        for line in filtered
        if line.lower().startswith("step ")
        or line.lower().startswith("problem:")
        or line.lower().startswith("exercise:")
        or line.lower().startswith("final answer:")
        or line.lower().startswith("diagram:")
        or line.lower().startswith("figure")
    ]
    narrated_steps = ordered_step_lines if ordered_step_lines else filtered

    question_intro = ""
    if problem_line:
        prompt_text = problem_line.split(":", 1)[1].strip()
        problem_no_text = problem_no_line.split(":", 1)[1].strip() if problem_no_line else ""
        # Format prompt for speech - convert symbols to spoken words
        spoken_prompt = _sanitize_for_speech(prompt_text)
        if len(spoken_prompt) > 220:
            spoken_prompt = spoken_prompt[:217].rstrip() + "..."
        target = _word_problem_target(prompt_text) if prompt_text else "the required value"
        
        # Include figure reference in intro if present
        figure_ref = ""
        if figure_line:
            figure_desc = figure_line.split(":", 1)[1].strip() if ":" in figure_line else figure_line
            if len(figure_desc) > 120:
                figure_desc = figure_desc[:117].rstrip() + "..."
            figure_ref = f" Look at the figure on the board. {figure_desc} "
        
        question_intro = (
            f"Now we will solve Problem no {problem_no_text}. First, let us read the question carefully: {spoken_prompt}. "
            f"{figure_ref}"
            f"We need to find {target}. Let me explain the solution step by step. "
        )

    if spoken and not is_placeholder:
        return f"{question_intro}{spoken}".strip()
    if narrated_steps:
        return f"{question_intro}{' '.join(narrated_steps[:2])}".strip()
    if compact_steps:
        return " ".join(compact_steps[:2])
    if teaching_language == "hi-IN":
        return f"{topic_title} ke current board steps complete ho gaye. Ab next explanation continue karte hain."
    if teaching_language == "gu-IN":
        return f"{topic_title} na current board steps complete thaya. Have next explanation continue kariye."
    return f"We finished the current board steps for {topic_title}. Now we will continue with the next explanation."


def _spoken_for_concept_board(steps: list[str], topic_title: str, teaching_language: str = "en-IN") -> str:
    lines = [str(step).strip() for step in steps if str(step).strip()]
    chapter_name = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("chapter:")), "")
    topic_line = next((line for line in lines if line.lower().startswith("topic ")), "")
    meaning = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("meaning:")), "")
    why = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("why it matters:")), "")
    chapter_flow = any("today's flow" in line.lower() for line in lines)
    chapter_topic_list = [
        line for line in lines
        if re.match(r"^\d+\.\s+", line.strip())
    ][:6]
    concept_steps = [
        line.split(":", 1)[1].strip()
        for line in lines
        if line.lower().startswith("concept step ")
    ][:4]

    if chapter_flow:
        topic_text = ", ".join(chapter_topic_list)
        if teaching_language == "hi-IN":
            return (
                f"Aaj hum {chapter_name or topic_title} chapter start kar rahe hain. "
                "Pehle main chapter ka roadmap board par likhunga, phir har topic ka concept samjhaunga, "
                "aur uske baad NCERT exercise solve karenge. "
                f"Is chapter ke topics hain: {topic_text}."
            ).strip()
        if teaching_language == "gu-IN":
            return (
                f"Aaje aapde {chapter_name or topic_title} chapter start kariye chhiye. "
                "Pehla hu chapter no roadmap board par lakhish, pachi darek topic no concept samjavish, "
                "ane tyaar baad NCERT exercise solve karishu. "
                f"Aa chapter na topics chhe: {topic_text}."
            ).strip()
        return (
            f"Today we are starting the {chapter_name or topic_title} chapter. "
            "First I am writing the chapter roadmap on the board, then I will explain each topic concept, "
            "and after that we will solve the NCERT exercise. "
            f"The topics in this chapter are: {topic_text}."
        ).strip()

    if teaching_language == "hi-IN":
        spoken_parts = [f"Ab {topic_title} samajhte hain."]
        if topic_line:
            spoken_parts.append(f"Board par main {topic_line} likh raha hoon.")
        if meaning:
            spoken_parts.append(f"Iska meaning hai: {meaning}")
        if why:
            spoken_parts.append(f"Intuition yeh hai: {why}")
        if concept_steps:
            spoken_parts.append("Ab board work dekho: " + " ".join(concept_steps))
        spoken_parts.append("Is concept ko dhyan se pakdo; ab hum isi flow mein aage badhenge.")
        return " ".join(spoken_parts)
    if teaching_language == "gu-IN":
        spoken_parts = [f"Have {topic_title} samajiye."]
        if topic_line:
            spoken_parts.append(f"Board par hu {topic_line} lakhish.")
        if meaning:
            spoken_parts.append(f"Aano meaning chhe: {meaning}")
        if why:
            spoken_parts.append(f"Intuition aa chhe: {why}")
        if concept_steps:
            spoken_parts.append("Have board work jovo: " + " ".join(concept_steps))
        spoken_parts.append("Aa concept dhyan thi samjo; have aapde aa flow ma aagal vadhishu.")
        return " ".join(spoken_parts)

    spoken_parts = [f"Now let us understand {topic_title}."]
    if topic_line:
        spoken_parts.append(f"I am writing {topic_line} on the board.")
    if meaning:
        spoken_parts.append(f"The meaning is: {meaning}")
    if why:
        spoken_parts.append(f"The intuition is: {why}")
    if concept_steps:
        spoken_parts.append("Now look at the board work: " + " ".join(concept_steps))
    spoken_parts.append("Hold this concept clearly; we will continue in the same flow.")
    return " ".join(spoken_parts)


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
        return f"Solve a similar PYQ-style variation {seed}: {problem}"
    return mutated


def _problem_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _problem_prompt_from_actions(actions: list[dict[str, Any]]) -> str:
    for action in actions:
        text = _action_text(action)
        if not text:
            continue
        if text.lower().startswith("problem:"):
            return text.split(":", 1)[1].strip()
    return ""


def _word_problem_target(prompt: str) -> str:
    question = str(prompt or "").strip()
    lowered = question.lower()
    match = re.search(
        r"\b(find|determine|calculate|evaluate|state|show|prove|express|factorise|what is|what are|how many)\b\s*(.+?)(?:\?|$)",
        lowered,
    )
    if match:
        target = match.group(2).strip(" .,:;")
        if target:
            return target
    if "what are q and r" in lowered:
        return "the quotient q and remainder r"
    if "express each number as a product of its prime factors" in lowered:
        return "the prime factorisation of the given number(s)"
    if lowered.startswith("express "):
        tail = re.sub(r"\(\s*[ivx]+\s*\)\s*[\d,\s]+$", "", question, flags=re.IGNORECASE).strip(" .")
        if tail:
            return tail
    return "the exact quantity asked in the question"


def _force_problem_readout_prefix(steps: list[str]) -> str:
    return ""


def _is_word_problem(prompt: str) -> bool:
    text = str(prompt or "").strip()
    if not text:
        return False
    lowered = text.lower()
    token_count = len(text.split())
    if token_count < 10:
        return False
    if any(symbol in text for symbol in ("=", "{", "}", "^", "+", "-", "*", "/", "subset", "intersection", "sqrt(")):
        return False
    if re.search(r"\b\d*[a-z]\s*[+\-*/]\s*[a-z]\b", lowered):
        return False
    return any(
        keyword in lowered
        for keyword in (
            "student",
            "person",
            "train",
            "minutes",
            "hours",
            "distance",
            "money",
            "rupees",
            "apples",
            "books",
            "class",
            "circular path",
            "starting point",
            "how many",
            "what is",
        )
    )


def _clean_step_text(step: str) -> str:
    cleaned = str(step or "").strip()
    cleaned = re.sub(r"(?i)^step\s*\d+\s*[:.)-]?\s*", "", cleaned).strip()
    return cleaned


def _normalize_board_math_style(step: str) -> str:
    text = str(step or "").strip()
    if not text:
        return text
    text = re.sub(r"\s*[×]\s*", " x ", text)
    text = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", " x ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = text.replace("=>", "=")
    # Prefer equation-chain style when step already has math content.
    if "=" in text and not text.lower().startswith(("step ", "final answer:", "problem", "chapter", "topic", "exercise")):
        text = text.replace(" = ", " = ")
    return text


def _prepend_tutoring_principles(problem_statement: str, steps: list[str]) -> list[str]:
    return steps


def _equation_rhs_factors(step: str) -> list[str]:
    text = str(step or "").strip()
    if "=" not in text:
        return []
    rhs = text.split("=", 1)[1]
    if "x" not in rhs and "×" not in rhs:
        return []
    parts = [p.strip() for p in re.split(r"[x×]", rhs) if p.strip()]
    factors: list[str] = []
    for part in parts:
        token = re.sub(r"[^A-Za-z0-9]", "", part)
        if token:
            factors.append(token)
    return factors


def _visualize_step_sequence(steps: list[str]) -> list[str]:
    # Keep board steps concise and human-teacher style; do not auto-inject
    # synthetic visualization lines that can duplicate or distort math.
    return [_normalize_board_math_style(str(step).strip()) for step in steps if str(step).strip()]


def _is_generic_diagram_hint(hint: str) -> bool:
    lowered = str(hint or "").strip().lower()
    if not lowered:
        return True
    generic_tokens = (
        "map known values",
        "choose the theorem",
        "choose the appropriate theorem",
        "simplify to the final result",
        "follow the chapter method",
        "show the flow",
    )
    return any(token in lowered for token in generic_tokens)


def _context_requests_diagram(prompt: str, solved_steps: list[str]) -> bool:
    _ = solved_steps
    prompt_text = str(prompt or "").strip().lower()
    if not prompt_text:
        return False

    explicit_markers = (
        "figure",
        "fig.",
        "diagram",
        "draw",
        "construct",
        "sketch",
        "in the figure",
        "in fig",
        "as shown",
        "given below",
    )
    if any(marker in prompt_text for marker in explicit_markers):
        return True

    geometry_markers = (
        "join ",
        "mark ",
        "tangent",
        "chord",
        "radius",
        "diameter",
        "label ",
        "bisector",
        "perpendicular",
    )
    return any(marker in prompt_text for marker in geometry_markers)


def _extract_point_labels(text: str, limit: int = 8) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"\b[A-Z]\b", str(text or "")):
        if token in seen:
            continue
        seen.add(token)
        labels.append(token)
        if len(labels) >= limit:
            break
    return labels


def _resolve_diagram_hint(prompt: str, solved_steps: list[str], diagram_hint: str | None) -> str | None:
    explicit_hint = str(diagram_hint or "").strip()
    if explicit_hint and not _is_generic_diagram_hint(explicit_hint):
        return explicit_hint

    if not _context_requests_diagram(prompt, solved_steps):
        return None

    context = " ".join([str(prompt or "").strip(), *[str(step).strip() for step in solved_steps if str(step).strip()]])
    lowered = context.lower()
    if not lowered:
        return explicit_hint or None

    if "circle" in lowered and ("tangent" in lowered or "chord" in lowered or "external point" in lowered):
        return (
            "Draw a circle with center O. Mark an external point A. Draw tangents AP and AQ touching the circle at P and Q. "
            "Join OA, OP, OQ and chord PQ."
        )
    if "circle" in lowered:
        return "Draw a circle and mark all given points and line segments from the question."
    if "triangle" in lowered:
        return "Draw the triangle with labelled vertices from the question and mark the given sides/angles."
    if "venn" in lowered or ("union" in lowered and "intersection" in lowered):
        return "Draw a two-set Venn diagram and label overlap and non-overlap regions."
    if "coordinate" in lowered or "graph" in lowered or "parabola" in lowered:
        return "Draw coordinate axes and plot the required points/curve from the question."

    labels = _extract_point_labels(context)
    if labels:
        return f"Draw the figure from the question and label points {', '.join(labels)}."

    return "Draw the required figure from the question and label all marked points."


def _is_short_diagram_label(label: str) -> bool:
    text = str(label or "").strip()
    if not text:
        return False
    if len(text) <= 20:
        return True
    return bool(re.match(r"^[A-Za-z0-9()\-_=]{1,24}$", text))


def _diagram_construction_steps(primitives: list[dict[str, Any]]) -> tuple[list[str], list[int | None]]:
    if not primitives:
        return [], []

    steps: list[str] = []
    primitive_step_map: list[int | None] = [None for _ in primitives]

    def ensure_step(text: str) -> int:
        for idx, existing in enumerate(steps, start=1):
            if existing.lower() == text.lower():
                return idx
        steps.append(text)
        return len(steps)

    # Circle/curve outlines are often represented by many unlabeled tiny line segments.
    unlabeled_lines = [
        idx
        for idx, action in enumerate(primitives)
        if str(action.get("action") or "").strip().lower() == "draw_line"
        and not str(action.get("label") or "").strip()
    ]
    if len(unlabeled_lines) >= 8:
        outline_step = ensure_step("Draw the main outline of the figure.")
        for idx in unlabeled_lines:
            primitive_step_map[idx] = outline_step

    for idx, action in enumerate(primitives):
        if primitive_step_map[idx] is not None:
            continue

        name = str(action.get("action") or "").strip().lower()
        label = str(action.get("label") or "").strip()
        step_text: str | None = None

        if name == "draw_line":
            step_text = f"Draw segment {label}." if label else "Draw the next required segment."
        elif name == "draw_angle":
            step_text = f"Mark angle {label}." if label else "Mark the required angle."
        elif name == "highlight_element":
            if label and _is_short_diagram_label(label):
                step_text = f"Mark point {label}."
        elif name == "write_text":
            if label and _is_short_diagram_label(label):
                if re.fullmatch(r"[A-Za-z]{1,2}", label):
                    step_text = f"Label point {label}."
                elif re.fullmatch(r"[A-Za-z]{2,5}", label):
                    step_text = f"Label segment {label}."

        if not step_text:
            continue
        primitive_step_map[idx] = ensure_step(step_text)

    if len(steps) > 6:
        steps = steps[:5] + ["Complete the remaining labels and required connections."]
        for idx, mapped in enumerate(primitive_step_map):
            if mapped is not None and mapped > 6:
                primitive_step_map[idx] = 6

    return steps, primitive_step_map


def _is_drawing_step_instruction(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    drawing_tokens = (
        "draw",
        "mark",
        "join",
        "label",
        "construct",
        "sketch",
        "plot",
        "bisect",
        "tangent",
        "chord",
        "radius",
        "diameter",
        "vertex",
        "line segment",
        "arc",
        "perpendicular",
        "parallel",
    )
    return any(token in lowered for token in drawing_tokens)


def _tokens_from_step_text(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"\b[A-Za-z]{1,4}\b", str(text or "")):
        upper = token.upper()
        if upper in {"STEP", "DRAW", "MARK", "JOIN", "WITH", "FROM", "THEN", "AND", "THE", "LET"}:
            continue
        if len(upper) == 1 and upper not in {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"}:
            continue
        tokens.add(upper)
    for token in re.findall(r"\b[A-Z]{2,5}\b", str(text or "")):
        tokens.add(token.upper())
    return tokens


def _tokens_from_primitive(action: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    label = str(action.get("label") or "").strip()
    content = str(action.get("content") or action.get("text") or "").strip()
    if label:
        tokens.update(_tokens_from_step_text(label))
    if content:
        tokens.update(_tokens_from_step_text(content))
    return tokens


def _solution_actions(
    *,
    exercise_label: str,
    problem_number: str,
    prompt: str,
    solved_steps: list[str],
    answer: str,
    source_label: str,
    diagram_hint: str | None = None,
    chapter_no: str | None = None,
    chapter_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Generate board actions for problem solution with proper formatting.
    - Formats math symbols in problem statement and steps
    - Includes figure/diagram rendering instructions
    - Provides step-by-step explanation flow
    """
    formatted_prompt = _format_for_display(prompt)
    cleaned_steps = [_clean_step_text(step) for step in solved_steps if _clean_step_text(step)]
    formatted_steps = [_format_for_display(step) for step in cleaned_steps]
    formatted_answer = _format_for_display(answer) if answer else ""
    resolved_diagram_hint = _resolve_diagram_hint(prompt, cleaned_steps, diagram_hint)
    formatted_diagram = _format_for_display(resolved_diagram_hint) if resolved_diagram_hint else None

    actions: list[dict[str, Any]] = [
        {"action": "draw_text", "content": f"Chapter no: {chapter_no or '-'}"},
        {"action": "draw_text", "content": f"Chapter name: {chapter_name or 'Current Topic'}"},
        {"action": "draw_text", "content": f"Topic name: {chapter_name or 'Current Topic'}"},
        {"action": "draw_text", "content": f"Exercise no: {exercise_label}"},
        {"action": "draw_text", "content": f"Problem no: {problem_number}"},
        {"action": "draw_text", "content": f"Problem statement: {formatted_prompt}"},
        {"action": "draw_text", "content": "Solution:"},
        {"action": "draw_text", "content": f"Source: {source_label}"},
    ]

    diagram_primitives: list[dict[str, Any]] = []
    construction_steps: list[str] = []
    primitive_construction_map: list[int | None] = []

    if formatted_diagram:
        try:
            given_label = f"What is given: {formatted_prompt.split('. ')[0][:120]}"
        except Exception:
            given_label = "What is given: (see problem statement)"
        target = _word_problem_target(formatted_prompt) if formatted_prompt else "the required value"
        need_label = f"What needs to be found: {target}"
        actions.append({"action": "write_text", "x": 10, "y": 80, "label": given_label, "metadata": {"diagram": True, "diagram_phase": 0}})
        actions.append({"action": "write_text", "x": 10, "y": 100, "label": need_label, "metadata": {"diagram": True, "diagram_phase": 0}})
        actions.append({"action": "draw_text", "content": f"Diagram: {formatted_diagram}", "metadata": {"diagram": True, "diagram_phase": 0}})
        actions.append({"action": "draw_shape", "content": formatted_diagram, "metadata": {"diagram": True, "diagram_phase": 0}})

        try:
            from ..services.geometry_translator import translate_diagram_to_primitives

            primitives = translate_diagram_to_primitives(formatted_diagram, model=None, max_attempts=1)
            if primitives:
                diagram_primitives = [dict(item) for item in primitives if isinstance(item, dict)]
        except Exception:
            diagram_primitives = []

    if formatted_diagram and diagram_primitives:
        if not any(_is_drawing_step_instruction(step) for step in formatted_steps[:6]):
            construction_steps, primitive_construction_map = _diagram_construction_steps(diagram_primitives)

    combined_steps = [*construction_steps, *formatted_steps]
    if not combined_steps and formatted_answer:
        combined_steps = ["Use the chapter method and compute step by step."]

    step_entries: list[tuple[int, str]] = []
    for index, step in enumerate(combined_steps[:14], start=1):
        line = f"Step {index}: {step}"
        actions.append({"action": "draw_text", "content": line})
        step_entries.append((index, line))

    if formatted_diagram and diagram_primitives:
        drawing_step_numbers = [number for number, line in step_entries if _is_drawing_step_instruction(line)]
        if not drawing_step_numbers and step_entries:
            drawing_step_numbers = [step_entries[0][0]]
        if not drawing_step_numbers:
            drawing_step_numbers = [1]

        first_drawing_step = drawing_step_numbers[0]
        for action in actions:
            if not isinstance(action, dict):
                continue
            metadata = action.get("metadata")
            if not isinstance(metadata, dict) or not metadata.get("diagram"):
                continue
            metadata["diagram_step"] = first_drawing_step

        drawing_steps_with_tokens: list[tuple[int, set[str]]] = [
            (number, _tokens_from_step_text(line))
            for number, line in step_entries
            if number in drawing_step_numbers
        ]
        bucket_count = max(1, len(drawing_step_numbers))
        primitive_total = max(1, len(diagram_primitives))

        for index, primitive in enumerate(diagram_primitives, start=1):
            primitive_copy = dict(primitive)
            primitive_meta = primitive_copy.get("metadata")
            if not isinstance(primitive_meta, dict):
                primitive_meta = {}

            mapped_from_construction = None
            if primitive_construction_map and index - 1 < len(primitive_construction_map):
                mapped_from_construction = primitive_construction_map[index - 1]

            if mapped_from_construction is not None and mapped_from_construction > 0:
                target_step = mapped_from_construction
            else:
                primitive_tokens = _tokens_from_primitive(primitive_copy)
                matched_step: int | None = None
                if primitive_tokens:
                    for number, step_tokens in drawing_steps_with_tokens:
                        if step_tokens and primitive_tokens.intersection(step_tokens):
                            matched_step = number
                            break
                target_bucket = min(bucket_count - 1, int(((index - 1) * bucket_count) / primitive_total))
                base_step = drawing_step_numbers[target_bucket]
                target_step = base_step
                if matched_step is not None and matched_step in drawing_step_numbers:
                    matched_index = drawing_step_numbers.index(matched_step)
                    target_step = drawing_step_numbers[max(target_bucket, matched_index)]

            primitive_meta.update(
                {
                    "diagram": True,
                    "diagram_phase": index,
                    "diagram_step": target_step,
                }
            )
            primitive_copy["metadata"] = primitive_meta
            actions.append(primitive_copy)

    if formatted_answer:
        actions.append({"action": "draw_text", "content": f"Final answer: {formatted_answer}"})

    return actions


def _extract_problem_metadata(actions: list[dict[str, Any]]) -> dict[str, str | None]:
    chapter_no = None
    chapter_name = None
    exercise_no = None
    problem_no = None
    problem_statement = None

    for action in actions:
        text = _action_text(action)
        if not text:
            continue
        value = text.strip()
        lowered = value.lower()
        if lowered.startswith("chapter no:"):
            chapter_no = value.split(":", 1)[1].strip() or None
        elif lowered.startswith("chapter name:"):
            chapter_name = value.split(":", 1)[1].strip() or None
        elif lowered.startswith("exercise no:"):
            exercise_no = value.split(":", 1)[1].strip() or None
        elif lowered.startswith("problem no:"):
            problem_no = value.split(":", 1)[1].strip() or None
        elif lowered.startswith("problem statement:"):
            problem_statement = value.split(":", 1)[1].strip() or None
        elif lowered.startswith("problem:") and not problem_statement:
            problem_statement = value.split(":", 1)[1].strip() or None

    return {
        "chapter_no": chapter_no,
        "chapter_name": chapter_name,
        "exercise_no": exercise_no,
        "problem_no": problem_no,
        "problem_statement": problem_statement,
    }


def _normalize_chapter_key(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").strip().lower().split())


def _chapter_number_for_session(session: StudentSession) -> str:
    try:
        grade = int(getattr(session, "grade", 10) or 10)
        exam = "jee" if str(getattr(session, "exam", "cbse")).lower() == "jee" else "cbse"
        if grade == 10 and exam == "cbse":
            chapter_name = _normalize_chapter_key(session.chapter_name or session.current_topic or "")
            curriculum = get_grade_curriculum(grade, exam)
            chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
            if isinstance(chapters, list):
                for idx, chapter in enumerate(chapters, start=1):
                    if not isinstance(chapter, dict):
                        continue
                    title = _normalize_chapter_key(chapter.get("title") or chapter.get("chapter") or "")
                    slug = _normalize_chapter_key(chapter.get("slug") or "")
                    if chapter_name and (chapter_name == title or chapter_name in title or title in chapter_name):
                        return str(get_pdf_chapter_number(grade, chapter, idx))
                for idx, chapter in enumerate(chapters, start=1):
                    if not isinstance(chapter, dict):
                        continue
                    slug = _normalize_chapter_key(chapter.get("slug") or "")
                    if chapter_name and (chapter_name == slug or chapter_name in slug or slug in chapter_name):
                        return str(get_pdf_chapter_number(grade, chapter, idx))

        return str(int(getattr(session, "current_chapter_index", 0) or 0) + 1)
    except Exception:
        try:
            return str(int(getattr(session, "current_chapter_index", 0) or 0) + 1)
        except Exception:
            return "1"


def _pdf_problem_actions_for_session(
    session: StudentSession,
    *,
    variation: int,
) -> list[dict[str, Any]] | None:
    exam = "jee" if str(getattr(session, "exam", "cbse")).lower() == "jee" else "cbse"
    grade = int(getattr(session, "grade", 10) or 10)
    if exam != "cbse" or grade != 10:
        return None

    chapter_name = _normalize_chapter_key(session.chapter_name or session.current_topic or "")
    curriculum = get_grade_curriculum(grade, exam)
    chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
    if not isinstance(chapters, list) or not chapters:
        return None

    matched_chapter = None
    matched_index = 0
    for idx, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        title = _normalize_chapter_key(chapter.get("title") or chapter.get("chapter") or "")
        slug = _normalize_chapter_key(chapter.get("slug") or "")
        if chapter_name and (
            chapter_name == title
            or chapter_name in title
            or title in chapter_name
            or chapter_name == slug
            or chapter_name in slug
            or slug in chapter_name
        ):
            matched_chapter = chapter
            matched_index = idx
            break
    if not isinstance(matched_chapter, dict):
        return None

    chapter_title = str(matched_chapter.get("title") or matched_chapter.get("chapter") or session.chapter_name or "Chapter")
    chapter_no = get_pdf_chapter_number(grade, matched_chapter, matched_index)
    if chapter_no <= 0:
        chapter_no = matched_index

    try:
        problems = load_chapter_pdf_exercises(grade, chapter_no, chapter_title)
    except Exception as error:
        print(f"CBSE PDF exercise loading skipped ({type(error).__name__}): {error}")
        return None
    if not problems:
        return None
    
    # Verify that the loaded PDF problems correspond to the matched chapter.
    # Some PDF files or chapter mapping may be missing or misaligned; in that case
    # return None so the caller can fall back to the topic-based actions.
    try:
        first_problem_title = str((problems[0].get("chapter_title") or "")).strip().lower()
        matched_title = str((matched_chapter.get("title") or matched_chapter.get("chapter") or matched_chapter.get("slug") or "")).strip().lower()
        if matched_title and first_problem_title and matched_title not in first_problem_title and first_problem_title not in matched_title:
            msg = f"CBSE PDF chapter mismatch: requested '{matched_title}' but loaded '{first_problem_title}' (chapter_no={chapter_no})"
            print(msg)
            # Return a safe, frontend-visible warning action so UI shows an explanatory message
            return [
                {"action": "draw_text", "content": f"NCERT chapter not found or mismatch for: {chapter_title}"},
                {"action": "draw_text", "content": "Please check curriculum JSON or PDF files for this chapter."},
                {"action": "draw_text", "content": msg},
            ]
    except Exception as err:
        # If any unexpected structure, return a safe frontend warning action
        msg = f"CBSE PDF chapter verification error: {type(err).__name__}: {err}"
        print(msg)
        return [
            {"action": "draw_text", "content": f"NCERT chapter not found: {chapter_title}"},
            {"action": "draw_text", "content": "An error occurred while validating the chapter mapping."},
            {"action": "draw_text", "content": msg},
        ]

    problem = problems[variation % len(problems)]
    # Pass session_id and current chapter context to prevent context loss
    solved = build_exercise_solution(problem, session_id=session.session_id, current_chapter=chapter_title)
    solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
    answer = str(solved.get("answer") or "").strip()
    exercise_label = str(problem.get("exercise") or "Exercise")
    problem_number = str(problem.get("number") or str((variation % len(problems)) + 1))
    prompt = str(problem.get("prompt") or "")
    return _solution_actions(
        exercise_label=exercise_label,
        problem_number=problem_number,
        prompt=prompt,
        solved_steps=solved_steps,
        answer=answer,
        source_label="NCERT Chapter Exercise",
        diagram_hint=solved.get("diagram"),
        chapter_no=str(chapter_no),
        chapter_name=chapter_title,
    )


def _ensure_problem_headers(
    session: StudentSession,
    actions: list[dict[str, Any]],
    *,
    fallback_problem_no: str,
) -> list[dict[str, Any]]:
    problem_meta = _extract_problem_metadata(actions)
    chapter_name = str(session.chapter_name or session.current_topic or "Current Chapter")
    topic_name = str(session.current_topic or session.chapter_name or "Current Topic")
    chapter_no = problem_meta.get("chapter_no") or _chapter_number_for_session(session)
    exercise_no = problem_meta.get("exercise_no") or "NCERT Exercise"
    problem_no = problem_meta.get("problem_no") or fallback_problem_no
    problem_statement = problem_meta.get("problem_statement") or _problem_prompt_from_actions(actions) or "-"

    filtered: list[dict[str, Any]] = []
    for action in actions:
        text = _action_text(action).lower()
        if text.startswith(("chapter no:", "chapter name:", "topic name:", "exercise no:", "problem no:", "problem statement:", "solution:")):
            continue
        filtered.append(action)

    source_lines: list[str] = []
    diagram_lines: list[str] = []
    final_answer_lines: list[str] = []
    raw_solution_lines: list[str] = []
    existing_step_actions: list[dict[str, Any]] = []
    preserved_diagram_actions: list[dict[str, Any]] = []

    def _is_diagram_action(action: dict[str, Any]) -> bool:
        action_name = str(action.get("action") or "").strip().lower()
        if action_name in {
            "draw_shape",
            "draw_coordinate_axes",
            "plot_curve",
            "draw_circle",
            "draw_line",
            "draw_angle",
            "highlight_element",
        }:
            return True
        metadata = action.get("metadata")
        if isinstance(metadata, dict) and metadata.get("diagram"):
            return True
        if action_name == "write_text":
            return isinstance(metadata, dict) and metadata.get("diagram")
        return False

    for action in filtered:
        text = _action_text(action)
        lowered = text.lower()
        if _is_diagram_action(action):
            preserved_diagram_actions.append(action)
        if not text:
            continue
        if lowered.startswith("source:"):
            source_lines.append(text)
            continue
        if lowered.startswith("diagram:"):
            diagram_lines.append(text)
            continue
        if lowered.startswith("final answer:"):
            final_answer_lines.append(text)
            continue
        if lowered.startswith("step "):
            raw_solution_lines.append(_clean_step_text(text))
            existing_step_actions.append(action)
            continue
        action_name = str(action.get("action") or "").strip().lower()
        if action_name in {"draw_text", "write_text", "write", "text", "add_text"}:
            raw_solution_lines.append(text)

    normalized_steps = [line.strip() for line in raw_solution_lines if str(line).strip()]
    normalized_steps = _prepend_tutoring_principles(problem_statement, normalized_steps)
    normalized_steps = _visualize_step_sequence(normalized_steps)
    if existing_step_actions:
        step_actions = existing_step_actions
    else:
        step_actions = [
            {"action": "draw_text", "content": f"Step {idx}: {line}"}
            for idx, line in enumerate(normalized_steps, start=1)
        ]

    headers = [
        {"action": "draw_text", "content": f"Chapter no: {chapter_no}"},
        {"action": "draw_text", "content": f"Chapter name: {chapter_name}"},
        {"action": "draw_text", "content": f"Topic name: {topic_name}"},
        {"action": "draw_text", "content": f"Exercise no: {exercise_no}"},
        {"action": "draw_text", "content": f"Problem no: {problem_no}"},
        {"action": "draw_text", "content": f"Problem statement: {problem_statement}"},
        {"action": "draw_text", "content": "Solution:"},
    ]
    extras = [{"action": "draw_text", "content": line} for line in [*source_lines[:1], *diagram_lines[:1]]]
    finals = [{"action": "draw_text", "content": line} for line in final_answer_lines[:1]]
    return [*headers, *extras, *preserved_diagram_actions, *step_actions, *finals]


def _topic_state_key(session: StudentSession) -> str:
    chapter = str(session.chapter_name or "").strip().lower()
    topic = _resolve_session_topic(session).strip().lower()
    return f"{chapter}|{topic}"


def _topic_problem_quota(topic: str, rag_context: str) -> int:
    candidates = _extract_problem_candidates(rag_context)
    topic_candidates = _best_topic_candidates(candidates, topic=topic, chapter=topic)
    if topic_candidates:
        return max(2, min(8, len(topic_candidates)))
    return 5


def _next_problem_actions_for_session(
    session: StudentSession,
    *,
    topic: str,
    rag_context: str,
    action: str,
) -> list[dict[str, Any]]:
    step_actions = {"next", "continue", "repeat", "next_exercise", "next_pdf_exercise", "start"}
    topic_switch_actions = {"next_topic", "next_chapter", "skip_topic", "skip_chapter"}

    cursors = dict(getattr(session, "topic_problem_cursors", {}) or {})
    history = dict(getattr(session, "topic_problem_history", {}) or {})
    quotas = dict(getattr(session, "topic_problem_quotas", {}) or {})
    key = _topic_state_key(session)
    seen = [entry for entry in history.get(key, []) if str(entry).strip()]
    seen_set = set(seen)

    if action in step_actions:
        quota = int(quotas.get(key) or _topic_problem_quota(topic, rag_context))
        quotas[key] = quota
        if len(seen) >= quota and action != "start":
            orchestrator._advance_to_next_topic(session)
            topic = _resolve_session_topic(session)
            rag_context = _rag_context_for_session(session, session.exam)
            key = _topic_state_key(session)
            seen = [entry for entry in history.get(key, []) if str(entry).strip()]
            seen_set = set(seen)
            quotas[key] = int(quotas.get(key) or _topic_problem_quota(topic, rag_context))
    elif action in topic_switch_actions:
        quotas[key] = int(quotas.get(key) or _topic_problem_quota(topic, rag_context))

    cursor = int(cursors.get(key, 0))

    pdf_probe = _pdf_problem_actions_for_session(session, variation=0)
    if pdf_probe is not None:
        pointer = int(cursors.get(key, -1))
        if action == "start":
            index = 0
        elif action == "previous_problem":
            index = max(pointer - 1, 0)
        elif action in {"refresh_problem", "repeat"}:
            index = max(pointer, 0)
        else:
            index = max(pointer + 1, 0)

        selected = _pdf_problem_actions_for_session(session, variation=index)
        if selected is None:
            index = 0
            selected = _pdf_problem_actions_for_session(session, variation=index)
        if selected is not None:
            cursors[key] = index
            session.topic_problem_cursors = cursors
            session.topic_problem_history = history
            session.topic_problem_quotas = quotas
            return selected

    selected_actions: list[dict[str, Any]] | None = None
    selected_key = ""

    for attempt in range(0, 18):
        variation = cursor + attempt
        candidate_actions = _pdf_problem_actions_for_session(session, variation=variation) or _topic_problem_actions(
            topic=topic,
            variation=variation,
            rag_context=rag_context,
            session_id=session.session_id,
        )
        prompt = _problem_prompt_from_actions(candidate_actions)
        prompt_key = _problem_key(prompt or " ".join(_steps_from_actions(candidate_actions)[:2]))
        if prompt_key and prompt_key not in seen_set:
            selected_actions = candidate_actions
            selected_key = prompt_key
            cursor = variation + 1
            break

    if selected_actions is None:
        selected_actions = _pdf_problem_actions_for_session(session, variation=cursor) or _topic_problem_actions(
            topic=topic,
            variation=cursor,
            rag_context=rag_context,
            session_id=session.session_id,
        )
        selected_key = _problem_key(
            _problem_prompt_from_actions(selected_actions) or " ".join(_steps_from_actions(selected_actions)[:2])
        )
        cursor += 1

    if selected_key:
        seen.append(selected_key)
        history[key] = seen[-80:]
    else:
        history[key] = seen[-80:]
    cursors[key] = cursor

    session.topic_problem_cursors = cursors
    session.topic_problem_history = history
    session.topic_problem_quotas = quotas
    return selected_actions


def _voice_chunks_from_steps(spoken_response: str, steps: list[str]) -> list[str]:
    candidate_chunks = [
        str(step).strip()
        for step in steps
        if str(step).strip().lower().startswith("step ")
    ]
    if candidate_chunks:
        return candidate_chunks[:14]
    final_only = [str(step).strip() for step in steps if str(step).strip().lower().startswith("final answer:")]
    if final_only:
        return final_only[:1]
    fallback = _steps_from_spoken_response(spoken_response, limit=12)
    return fallback if fallback else ([spoken_response] if spoken_response else [])


def _pyq_problem_actions(topic: str, rag_context: str, variation: int = 0, session_id: str | None = None) -> list[dict[str, Any]]:
    candidates = _extract_problem_candidates(rag_context)
    topic_candidates = _best_topic_candidates(candidates, topic=topic, chapter=topic)
    pool = topic_candidates or candidates
    if pool:
        base_problem = pool[variation % len(pool)]
        cycle = variation // max(1, len(pool))
        prompt = base_problem if cycle == 0 else _generate_similar_problem(base_problem, cycle + 1)
    else:
        base_problem = f"Solve one step-by-step problem based on {topic or 'the current topic'}."
        prompt = _generate_similar_problem(base_problem, variation + 1)

    lowered_context = (rag_context or "").lower()
    if "ncert" in lowered_context or "cbse" in lowered_context:
        source_label = "NCERT Exercise"
        exercise_label = "NCERT Practice"
    else:
        source_label = "PYQ Pattern"
        exercise_label = "PYQ Practice"

    # Pass session_id and topic context to prevent context loss
    solved = build_exercise_solution(
        {
            "chapter_title": topic or "Mathematics",
            "exercise": exercise_label,
            "number": str(variation + 1),
            "prompt": prompt,
        },
        session_id=session_id,
        current_chapter=topic,
    )
    solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
    answer = str(solved.get("answer") or "").strip()
    return _solution_actions(
        exercise_label=exercise_label,
        problem_number=str(variation + 1),
        prompt=prompt,
        solved_steps=solved_steps,
        answer=answer,
        source_label=source_label,
        diagram_hint=solved.get("diagram") or "Map known values, choose the theorem/formula, then simplify to the final result.",
    )


def _topic_problem_actions(topic: str, variation: int = 0, rag_context: str = "", session_id: str | None = None) -> list[dict[str, Any]]:
    lowered = (topic or "").lower()

    if "euclid" in lowered or "division lemma" in lowered:
        divisor = 7 + (variation % 23)
        quotient = 8 + ((variation * 2) % 17)
        remainder = 1 + ((variation * 5) % max(1, divisor - 1))
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
        return _solution_actions(
            exercise_label="Euclid's Division Lemma",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=answer,
            source_label="Chapter Exercise",
            diagram_hint=solved.get("diagram") or "Use a = bq + r and split dividend into quotient-part plus remainder.",
        )

    if "hcf" in lowered or "lcm" in lowered or "euclid algorithm" in lowered:
        hcf_base = 3 + (variation % 13)
        hcf = 4 + (variation % 11)
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
        return _solution_actions(
            exercise_label="Revisiting HCF and LCM",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=answer,
            source_label="Chapter Exercise",
            diagram_hint=solved.get("diagram") or "Create the Euclid remainder chain until remainder becomes zero.",
        )

    if "decimal expansion" in lowered:
        if variation % 2 == 0:
            pow2 = 3 + (variation % 6)
            pow5 = 1 + (variation % 5)
            denominator = (2 ** pow2) * (5 ** pow5)
            numerator = 3 + (variation % 17)
        else:
            denominator = (2 ** (2 + (variation % 5))) * (3 + (variation % 11))
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
        return _solution_actions(
            exercise_label="Decimal Expansions",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=answer,
            source_label="Chapter Exercise",
            diagram_hint=solved.get("diagram") or "Prime-factor tree of denominator: keep only 2 and 5 for terminating decimals.",
        )

    if "irrational" in lowered:
        radicals = [2, 3, 5, 7, 11, 13, 17]
        radicand = radicals[variation % len(radicals)]
        coefficient = 2 + (variation % 13)
        constant = 3 + ((variation * 3) % 19)
        prompt = f"Show that {constant} + {coefficient}sqrt({radicand}) is irrational."
        # Pass session_id and topic context to prevent context loss
        solved = build_exercise_solution(
            {
                "chapter_title": "Real Numbers",
                "exercise": "Irrational Numbers",
                "number": str(variation + 1),
                "prompt": prompt,
            },
            session_id=session_id,
            current_chapter=topic,
        )
        solved_steps = [str(step).strip() for step in solved.get("steps", []) if str(step).strip()]
        answer = str(solved.get("answer") or "").strip()
        return _solution_actions(
            exercise_label="Irrational Numbers",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=answer,
            source_label="Chapter Exercise",
            diagram_hint=solved.get("diagram") or "Contradiction flow: assume rational -> derive impossible statement -> conclude irrational.",
        )

    if "set notation" in lowered or "representations" in lowered:
        alt = variation % 2
        if alt == 0:
            start = 2 + (variation % 5)
            end = start + 4
            prompt = f"Write B in roster form if B = {{x in N | {start} <= x <= {end}}}."
            solved_steps = [
                f"Natural numbers from {start} to {end} are written one by one, because roster form lists elements explicitly.",
                f"B = {{{','.join(str(item) for item in range(start, end + 1))}}}.",
            ]
            return [
                *_solution_actions(
                    exercise_label="Set notation and representations",
                    problem_number=str(variation + 1),
                    prompt=prompt,
                    solved_steps=solved_steps,
                    answer=f"B = {{{','.join(str(item) for item in range(start, end + 1))}}}",
                    source_label="Chapter Exercise",
                    diagram_hint="Map set-builder condition to consecutive numbers on a number line.",
                ),
            ]
        base = 3 + (variation % 4)
        prompt = f"Convert A = {{{base},{2*base},{3*base},{4*base}}} into set-builder form."
        solved_steps = [
            "Observe each element is a multiple of the same base number.",
            f"Let x = {base}n where n is a natural number from 1 to 4.",
            f"A = {{x in N | x = {base}n, 1 <= n <= 4}}.",
        ]
        return [
            *_solution_actions(
                exercise_label="Set notation and representations",
                problem_number=str(variation + 1),
                prompt=prompt,
                solved_steps=solved_steps,
                answer=f"A = {{x in N | x = {base}n, 1 <= n <= 4}}",
                source_label="Chapter Exercise",
                diagram_hint="Group equal jumps of size base on a number line to show the pattern.",
            ),
        ]

    if "subset" in lowered or "types of sets" in lowered:
        base = 1 + (variation % 4)
        set_a = [base, base + 1, base + 2]
        set_b = [base - 1, *set_a, base + 3, base + 4]
        prompt = f"Check whether A = {{{','.join(str(item) for item in set_a)}}} is a proper subset of B = {{{','.join(str(item) for item in set_b)}}}."
        solved_steps = [
            "List each element of A and verify it appears in B.",
            "Since every element of A is present in B, A is a subset of B.",
            "Because B has extra elements not in A, A is a proper subset of B.",
        ]
        return _solution_actions(
            exercise_label="Types of sets and subset relations",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer="A is a proper subset of B.",
            source_label="Chapter Exercise",
            diagram_hint="Draw two nested circles with A fully inside B.",
        )

    if "operation" in lowered:
        start = 1 + (variation % 4)
        set_a = [start, start + 1, start + 2, start + 3]
        set_b = [start + 2, start + 3, start + 4, start + 5]
        union = sorted(set(set_a) | set(set_b))
        inter = sorted(set(set_a) & set(set_b))
        diff_ab = [value for value in set_a if value not in set_b]
        diff_ba = [value for value in set_b if value not in set_a]
        prompt = f"For A = {{{','.join(map(str, set_a))}}} and B = {{{','.join(map(str, set_b))}}}, find A union B, A intersection B, A - B, and B - A."
        solved_steps = [
            f"Union combines all unique elements: A union B = {{{','.join(map(str, union))}}}.",
            f"Intersection keeps common elements: A intersection B = {{{','.join(map(str, inter))}}}.",
            f"Difference A - B keeps elements only in A: {{{','.join(map(str, diff_ab))}}}.",
            f"Difference B - A keeps elements only in B: {{{','.join(map(str, diff_ba))}}}.",
        ]
        return _solution_actions(
            exercise_label="Operations on sets",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=f"A union B = {{{','.join(map(str, union))}}}, A intersection B = {{{','.join(map(str, inter))}}}",
            source_label="Chapter Exercise",
            diagram_hint="Venn diagram with overlap for intersection and side regions for differences.",
        )

    if "venn" in lowered:
        total = 35 + (variation % 16)
        c_like = 18 + (variation % 10)
        f_like = 14 + (variation % 9)
        both = 6 + (variation % 7)
        only_c = c_like - both
        only_f = f_like - both
        neither = total - (only_c + only_f + both)
        prompt = (
            f"In a class of {total} students, {c_like} like Cricket, {f_like} like Football, "
            f"and {both} like both. Find only-Cricket, only-Football, and neither."
        )
        solved_steps = [
            f"Only Cricket = {c_like} - {both} = {only_c}, because both-likers are counted in Cricket total.",
            f"Only Football = {f_like} - {both} = {only_f}, for the same reason.",
            f"Students liking at least one game = {only_c} + {both} + {only_f} = {only_c + both + only_f}.",
            f"Neither = total - at least one = {total} - {only_c + both + only_f} = {neither}.",
        ]
        return _solution_actions(
            exercise_label="Venn diagram applications",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=f"Only Cricket = {only_c}, Only Football = {only_f}, Neither = {neither}",
            source_label="Chapter Exercise",
            diagram_hint="Two-circle Venn diagram: left-only, overlap, right-only, and outside region.",
        )

    if "ordered pair" in lowered or "cartesian" in lowered:
        first = 1 + (variation % 3)
        set_a = [first, first + 1]
        labels = ["a", "b", "c", "d"]
        set_b = [labels[(variation + 0) % len(labels)], labels[(variation + 1) % len(labels)]]
        cartesian_pairs = [f"({x},{y})" for x in set_a for y in set_b]
        relation = [f"({set_a[0]},{set_b[0]})", f"({set_a[1]},{set_b[1]})"]
        prompt = f"For A = {{{set_a[0]},{set_a[1]}}} and B = {{{set_b[0]},{set_b[1]}}}, form A x B and one relation R from A to B."
        solved_steps = [
            "Cartesian product contains every ordered pair with first element from A and second from B.",
            f"A x B = {{{','.join(cartesian_pairs)}}}.",
            f"Choose any valid subset of A x B as relation, e.g. R = {{{','.join(relation)}}}.",
        ]
        return _solution_actions(
            exercise_label="Relations and functions basics",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer=f"R = {{{','.join(relation)}}}",
            source_label="Chapter Exercise",
            diagram_hint="Arrow diagram from each element of A to selected elements of B.",
        )

    if "relation" in lowered:
        base = 1 + (variation % 3)
        a = [base, base + 1, base + 2]
        prompt = (
            f"On A = {{{a[0]},{a[1]},{a[2]}}}, let R = "
            f"{{({a[0]},{a[0]}),({a[1]},{a[1]}),({a[2]},{a[2]}),({a[0]},{a[1]}),({a[1]},{a[0]})}}. "
            "Check reflexive and symmetric properties."
        )
        solved_steps = [
            "Reflexive test: all pairs (a,a) for each element of A must be present.",
            "Here (1,1)-type pairs for all elements are present, so relation is reflexive.",
            "Symmetric test: if (x,y) is present then (y,x) must also be present.",
            "Since both cross-pairs are present, relation is symmetric.",
        ]
        return _solution_actions(
            exercise_label="Relation properties",
            problem_number=str(variation + 1),
            prompt=prompt,
            solved_steps=solved_steps,
            answer="R is reflexive and symmetric.",
            source_label="Chapter Exercise",
            diagram_hint="Relation matrix or arrow diagram to verify mirror pairs.",
        )

    # Fallback to PYQ problems with session context
    return _pyq_problem_actions(topic=topic, rag_context=rag_context, variation=variation, session_id=session_id)


def _prepare_problem_whiteboard_actions(
    topic: str,
    actions: list[dict[str, Any]],
    variation: int,
    rag_context: str = "",
    session_id: str | None = None,
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
        return _topic_problem_actions(topic, variation=variation, rag_context=rag_context, session_id=session_id)
    return cleaned


def _peek_next_problem(session: StudentSession, *, topic: str, rag_context: str) -> list[dict[str, Any]] | None:
    """Return the next problem actions without mutating session cursors/history.

    This computes the candidate for the next cursor position and returns the actions so
    the caller can cache or pre-render them for instant delivery.
    """
    try:
        key = _topic_state_key(session)
        cursors = dict(getattr(session, "topic_problem_cursors", {}) or {})
        cursor = int(cursors.get(key, 0))
        # Peek the next variation
        variation = max(0, cursor + 1)
        pdf_probe = _pdf_problem_actions_for_session(session, variation=variation)
        if pdf_probe is not None:
            return pdf_probe
        # Use topic actions generator with session context
        return _topic_problem_actions(topic=topic, variation=variation, rag_context=rag_context, session_id=session.session_id)
    except Exception:
        return None


def _warm_problem_cache(session: StudentSession, topic: str, rag_context: str, count: int = 3) -> None:
    """Warm the exercise solution cache for the next `count` problems to reduce latency.

    Calls `build_exercise_solution` for upcoming problems using session context. Silent on errors.
    """
    try:
        key = _topic_state_key(session)
        cursors = dict(getattr(session, "topic_problem_cursors", {}) or {})
        cursor = int(cursors.get(key, 0))
        for i in range(1, count + 1):
            variation = cursor + i
            # Peek candidate problem
            candidate = _pdf_problem_actions_for_session(session, variation=variation) or _topic_problem_actions(topic=topic, variation=variation, rag_context=rag_context, session_id=session.session_id)
            if not candidate:
                continue
            prompt = _problem_prompt_from_actions(candidate)
            problem = {
                "chapter_title": topic or session.chapter_name,
                "exercise": "Prefetch",
                "number": str(variation + 1),
                "prompt": prompt,
            }
            # Build solution to warm cache (non-blocking best-effort)
            try:
                build_exercise_solution(problem, session_id=session.session_id, current_chapter=topic)
            except Exception:
                continue
    except Exception:
        return


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


_CURRICULUM_STEP_ACTIONS = {
    "start",
    "next",
    "continue",
    "repeat",
    "refresh_problem",
    "previous_problem",
    "next_exercise",
    "next_pdf_exercise",
    "next_topic",
    "next_chapter",
    "skip_topic",
    "skip_chapter",
    "homework",
    "finish",
    "end",
}


def _extract_chat_question(input_data: dict[str, Any]) -> str:
    for field in ("question", "message", "text"):
        value = input_data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _looks_like_question(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    if "?" in lowered:
        return True
    return bool(
        re.match(
            r"^(what|why|how|when|where|which|who|can|could|would|should|is|are|do|does|did)\b",
            lowered,
        )
        or any(
            phrase in lowered
            for phrase in (
                "explain",
                "i have a doubt",
                "i don't understand",
                "i do not understand",
                "not clear",
                "confused",
                "help me understand",
            )
        )
    )


def _should_route_as_doubt(input_data: dict[str, Any]) -> tuple[bool, str]:
    question = _extract_chat_question(input_data)
    if not question or input_data.get("answer"):
        return False, question

    action = _normalize_action(input_data)
    has_explicit_curriculum_action = action in _CURRICULUM_STEP_ACTIONS
    is_explicit_doubt_action = action in {"ask", "question", "doubt", "chat", "help", "unable", "not_able"}

    if is_explicit_doubt_action or _looks_like_question(question):
        return True, question
    if not action:
        return True, question
    if not has_explicit_curriculum_action and ("message" in input_data or "text" in input_data):
        return True, question
    return False, question


def _seed_doubt_state_from_class_context(state, session: StudentSession | None, input_data: dict[str, Any]) -> None:
    if session is not None:
        for attr in ("grade", "exam", "current_topic", "chapter_name", "current_problem"):
            value = getattr(session, attr, None)
            if value:
                if attr == "chapter_name":
                    setattr(state, "chapter_label", value)
                    if not getattr(state, "topic_title", None):
                        setattr(state, "topic_title", value)
                else:
                    setattr(state, attr, value)

    board_problem = str(input_data.get("board_problem") or "").strip()
    whiteboard_context = input_data.get("whiteboard_context") if isinstance(input_data.get("whiteboard_context"), dict) else {}
    if not board_problem and isinstance(whiteboard_context, dict):
        board_problem = str(whiteboard_context.get("problem") or "").strip()

    if board_problem:
        state.active_problem = {"prompt": board_problem}
        state.current_problem = {"prompt": board_problem}

    board_steps = input_data.get("board_steps")
    if isinstance(board_steps, list):
        state.whiteboard = {
            "problem": board_problem,
            "chalk_lines": [str(step) for step in board_steps if str(step).strip()],
        }
    elif isinstance(whiteboard_context, dict) and whiteboard_context:
        state.whiteboard = whiteboard_context


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
    if action in {"previous_problem", "refresh_problem"}:
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


def _normalize_teaching_text(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").lower().split())


def _chapter_for_session(session: StudentSession) -> dict[str, Any]:
    try:
        curriculum = get_grade_curriculum(int(getattr(session, "grade", 10) or 10), getattr(session, "exam", "cbse"))
    except Exception:
        return {}

    chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
    if not isinstance(chapters, list):
        return {}

    index = int(getattr(session, "current_chapter_index", 0) or 0)
    if 0 <= index < len(chapters) and isinstance(chapters[index], dict):
        return chapters[index]

    wanted = _normalize_teaching_text(getattr(session, "chapter_name", ""))
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        labels = [chapter.get("slug"), chapter.get("title"), chapter.get("chapter"), chapter.get("name")]
        if any(wanted and wanted in _normalize_teaching_text(label) for label in labels):
            return chapter
    return {}


def _concept_for_chapter_topic(chapter: dict[str, Any], topic: str) -> dict[str, Any]:
    concepts = chapter.get("concepts") if isinstance(chapter, dict) else []
    if not isinstance(concepts, list):
        return {}
    wanted = _normalize_teaching_text(topic)
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        labels = [concept.get("id"), concept.get("title"), concept.get("definition")]
        for label in labels:
            normalized = _normalize_teaching_text(label)
            if wanted and normalized and (wanted == normalized or wanted in normalized or normalized in wanted):
                return concept
    return {}


def _topic_teaching_fallback(topic: str, chapter: dict[str, Any]) -> tuple[str, str, list[str], str]:
    lowered = _normalize_teaching_text(topic)
    summary = str(chapter.get("summary") or "").strip()
    anchor = str(chapter.get("teaching_anchor") or "").strip()
    goal = str(chapter.get("classroom_goal") or "").strip()

    if "hcf" in lowered or "lcm" in lowered:
        return (
            "HCF is the greatest common factor; LCM is the least common multiple.",
            "We compare prime factors: common smallest powers give HCF, highest powers give LCM.",
            ["Example numbers: 24 = 2 x 2 x 2 x 3", "36 = 2 x 2 x 3 x 3", "Common factors give HCF; all highest powers give LCM."],
            "Draw two prime-factor rows and circle common factors.",
        )
    if "decimal" in lowered and "rational" in lowered:
        return (
            "For p/q in lowest terms, the decimal terminates only when q has prime factors 2 and/or 5.",
            "Reduce the fraction first, then inspect the denominator's prime factors.",
            ["13/160 is in lowest terms.", "160 = 2 x 2 x 2 x 2 x 2 x 5.", "Only 2 and 5 appear, so decimal terminates."],
            "Draw a denominator factor tree and highlight factors 2 and 5.",
        )
    if "irrational" in lowered:
        return (
            "An irrational number cannot be written as p/q where p and q are integers and q is not zero.",
            "We often prove this by contradiction: assume rational, simplify, and reach an impossible result.",
            ["Assume sqrt(2) = p/q in lowest terms.", "Squaring gives p^2 = 2q^2.", "Both p and q become even, contradiction."],
            "Draw a contradiction flow: assume rational -> both even -> impossible.",
        )
    if "zero" in lowered and "polynomial" in lowered:
        return (
            "A zero of a polynomial is a value of x that makes the polynomial equal to 0.",
            "We substitute or factorise to find where the expression becomes zero.",
            ["For p(x) = x - 3, put x = 3.", "p(3) = 3 - 3 = 0.", "So 3 is a zero."],
            "Draw a number line and mark the zero point.",
        )
    return (
        anchor or f"{topic} is a core idea in this chapter.",
        goal or summary or f"We learn the meaning, rule, and one board example for {topic}.",
        [f"Meaning of {topic}", "Important rule/formula", "One small board example"],
        "Draw a simple concept map: meaning -> rule -> example.",
    )


def _chapter_teaching_phase_actions(session: StudentSession) -> list[dict[str, Any]] | None:
    chapter = _chapter_for_session(session)
    chapter_title = str(chapter.get("title") or session.chapter_name or "Current Chapter").strip()
    topics = [str(item).strip() for item in (session.agenda or []) if str(item).strip()]
    if not topics:
        topics = [chapter_title]

    if not getattr(session, "class_intro_done", False):
        session.class_intro_done = True
        session.concept_teaching_index = 0
        session.concept_teaching_complete = False
        session.exercise_phase_started = False
        actions: list[dict[str, Any]] = [
            {"action": "draw_text", "content": f"Chapter: {chapter_title}"},
            {"action": "draw_text", "content": "Today's flow: concepts first, then NCERT exercises."},
            {"action": "draw_text", "content": "Topics in this chapter:"},
        ]
        for index, topic in enumerate(topics, start=1):
            actions.append({"action": "draw_text", "content": f"{index}. {topic}"})
        if chapter.get("summary"):
            actions.append({"action": "draw_text", "content": f"Chapter idea: {chapter.get('summary')}"})
        actions.append({"action": "draw_shape", "content": "Chapter roadmap with topic boxes connected left to right."})
        return actions

    if not getattr(session, "concept_teaching_complete", False):
        index = int(getattr(session, "concept_teaching_index", 0) or 0)
        index = max(0, min(index, len(topics) - 1))
        topic = topics[index]
        session.current_topic_index = index
        session.current_topic = topic

        concept = _concept_for_chapter_topic(chapter, topic)
        fallback_definition, fallback_explanation, fallback_board_work, diagram_hint = _topic_teaching_fallback(topic, chapter)
        definition = str(concept.get("definition") or fallback_definition).strip()
        explanation = str(concept.get("explanation") or fallback_explanation).strip()
        board_work = concept.get("board_work") if isinstance(concept.get("board_work"), list) else fallback_board_work

        actions = [
            {"action": "draw_text", "content": f"Chapter: {chapter_title}"},
            {"action": "draw_text", "content": f"Topic {index + 1}/{len(topics)}: {topic}"},
            {"action": "draw_text", "content": f"Meaning: {definition}"},
            {"action": "draw_text", "content": f"Why it matters: {explanation}"},
            {"action": "draw_text", "content": "Blackboard build:"},
        ]
        for step_index, item in enumerate(board_work[:5], start=1):
            text = str(item or "").strip()
            if text:
                actions.append({"action": "draw_text", "content": f"Concept step {step_index}: {text}"})

        examples = concept.get("ncert_examples") if isinstance(concept.get("ncert_examples"), list) else []
        if examples and isinstance(examples[0], dict):
            example = examples[0]
            if example.get("prompt"):
                actions.append({"action": "draw_text", "content": f"Mini example: {example.get('prompt')}"})
            for step_index, step in enumerate((example.get("steps") or [])[:3], start=1):
                actions.append({"action": "draw_text", "content": f"Example step {step_index}: {step}"})
        actions.append({"action": "draw_text", "content": "Check: understand the idea before exercise practice."})
        actions.append({"action": "draw_text", "content": f"Diagram: {diagram_hint}"})
        actions.append({"action": "draw_shape", "content": diagram_hint})
        if any(word in _normalize_teaching_text(topic) for word in ["coordinate", "graph", "polynomial", "zero"]):
            actions.append({"action": "draw_coordinate_axes", "content": diagram_hint})

        session.concept_teaching_index = index + 1
        if session.concept_teaching_index >= len(topics):
            session.concept_teaching_complete = True
        return actions

    if not getattr(session, "exercise_phase_started", False):
        session.exercise_phase_started = True
        session.current_topic_index = 0
        session.current_topic = topics[0]
        return [
            {"action": "draw_text", "content": f"Chapter concepts complete: {chapter_title}"},
            {"action": "draw_text", "content": "Now we start NCERT exercise solving step by step."},
            {"action": "draw_text", "content": "Exercise flow: read problem -> identify concept -> solve on board -> final answer."},
            {"action": "draw_shape", "content": "Flow diagram from concept notes to exercise problem solving."},
        ]

    return None


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
            "pace": "steady",
            "sync_to_whiteboard": True,
            "pause_ms": 220,
        },
        "avatar_stream": {
            "voice_chunks": [spoken_response],
            "steps": [
                f"Session complete: {session.class_duration_minutes} minutes",
                "Review today's notes and homework.",
            ],
            "pace": "steady",
            "pause_ms": 220,
        },
    }


def _rag_context_for_session(session: StudentSession, exam_type: str) -> str:
    topic = (
        _resolve_session_topic(session)
        or session.chapter_name
    )
    chapter = session.chapter_name or topic
    normalized_exam = "jee" if str(exam_type or "").lower() == "jee" else "cbse"
    grade = int(getattr(session, "grade", 10) or 10)
    cache_key = (
        grade,
        normalized_exam,
        str(chapter or "").strip().lower(),
        str(topic or "").strip().lower(),
    )
    cached_context = _RAG_CONTEXT_CACHE.get(cache_key)
    if cached_context is not None:
        return cached_context

    source_hint = (
        "JEE PYQ patterns, solved examples, and problem solving strategies"
        if normalized_exam == "jee"
        else "NCERT textbook concept explanations, worked examples, and exercise questions"
    )
    query = (
        f"Grade {grade} "
        f"{normalized_exam.upper()} Mathematics "
        f"ONLY chapter {chapter}. "
        f"Current topic {topic}. "
        f"{source_hint}. Ignore unrelated chapters."
    ).strip()

    try:
        curriculum = get_grade_curriculum(grade, normalized_exam)
        chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
        if isinstance(chapters, list) and chapters:
            chapter_match = None
            chapter_l = str(chapter or "").strip().lower()
            topic_l = str(topic or "").strip().lower()
            for item in chapters:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("chapter") or "").strip()
                slug = str(item.get("slug") or "").strip()
                title_l = title.lower()
                slug_l = slug.lower()
                if chapter_l and (chapter_l in title_l or title_l in chapter_l or chapter_l == slug_l):
                    chapter_match = item
                    break
                if topic_l and (topic_l in title_l or topic_l == slug_l):
                    chapter_match = item
                    break

            if isinstance(chapter_match, dict):
                lines: list[str] = []
                lines.append(f"Chapter: {chapter_match.get('title') or chapter_match.get('chapter') or chapter}")
                if chapter_match.get("summary"):
                    lines.append(f"Summary: {chapter_match.get('summary')}")
                if chapter_match.get("teaching_anchor"):
                    lines.append(f"Anchor: {chapter_match.get('teaching_anchor')}")
                if chapter_match.get("classroom_goal"):
                    lines.append(f"Goal: {chapter_match.get('classroom_goal')}")
                for concept in chapter_match.get("concepts", [])[:6]:
                    if not isinstance(concept, dict):
                        continue
                    if concept.get("title"):
                        lines.append(f"Concept: {concept.get('title')}")
                    if concept.get("definition"):
                        lines.append(f"Definition: {concept.get('definition')}")
                    if concept.get("explanation"):
                        lines.append(f"Explanation: {concept.get('explanation')}")
                    for bw in (concept.get("board_work") or [])[:4]:
                        lines.append(str(bw))
                    for example in (concept.get("ncert_examples") or [])[:4]:
                        if isinstance(example, dict) and example.get("prompt"):
                            lines.append(f"Exercise question: {example.get('prompt')}")
                        for step in (example.get("steps") or [])[:5]:
                            lines.append(f"Step: {step}")

                firebase_context = "\n".join(str(line).strip() for line in lines if str(line).strip())
                if len(firebase_context) >= 200:
                    scoped_context = _scope_rag_context_to_chapter(firebase_context, chapter=chapter, topic=topic)
                    _RAG_CONTEXT_CACHE[cache_key] = scoped_context
                    return scoped_context
    except Exception as error:
        print(f"Firestore curriculum grounding failed ({type(error).__name__}): {error}")

    try:
        raw_phase = getattr(session, "active_phase", "teaching")
        phase = str(getattr(raw_phase, "value", raw_phase) or "teaching").strip().lower()
        raw_context = retrieve_context(
            query=query,
            exam_type=normalized_exam,
            k=12,
            grade=grade,
            phase=phase,
        )
        scoped_context = _scope_rag_context_to_chapter(raw_context, chapter=chapter, topic=topic)
        _RAG_CONTEXT_CACHE[cache_key] = scoped_context
        return scoped_context
    except Exception as error:
        print(f"Tutor RAG lookup failed ({type(error).__name__}): {error}")
        _RAG_CONTEXT_CACHE[cache_key] = ""
        return ""


async def _handle_multi_agent_class(req: TutorRequest, input_data: dict[str, Any]) -> dict:
    session: StudentSession = orchestrator.get_or_create_session(req.session_id)
    route_context = dict(req.context or {})
    if "grade" not in route_context and input_data.get("grade") is not None:
        route_context["grade"] = input_data.get("grade")
    if "exam" not in route_context and req.get_exam():
        route_context["exam"] = req.get_exam()
    if input_data.get("chapter") is not None:
        route_context["chapter"] = input_data.get("chapter")
    if input_data.get("chapter_slug") is not None:
        route_context["chapter_slug"] = input_data.get("chapter_slug")

    if route_context.get("grade") is not None:
        try:
            session.grade = int(route_context["grade"])
        except (TypeError, ValueError):
            pass
    session.exam = "jee" if str(route_context.get("exam", req.get_exam())).lower() == "jee" else "cbse"
    session.teaching_language = _normalize_teaching_language(
        input_data.get("teaching_language")
        or route_context.get("teaching_language")
        or getattr(session, "teaching_language", "en-IN")
    )

    action = _normalize_action(input_data)
    # If no explicit action provided and no question/answer, auto-continue for a seamless class
    if not action and not input_data.get("answer") and not input_data.get("question"):
        action = "continue"
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
    # Warm cache on class start for smoother continuous experience
    if action == "start":
        try:
            _warm_problem_cache(session, topic=session.current_topic or session.chapter_name, rag_context=rag_context, count=3)
        except Exception:
            pass
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
    local_board_actions = {
        "start",
        "next",
        "continue",
        "repeat",
        "refresh_problem",
        "previous_problem",
        "next_exercise",
        "next_pdf_exercise",
        "next_topic",
        "next_chapter",
        "skip_topic",
        "skip_chapter",
    }
    can_use_local_board = (
        route != "proctor_agent"
        and action in local_board_actions
        and not input_data.get("answer")
        and not input_data.get("question")
    )

    if route == "proctor_agent":
        proctor_payload = await proctor_agent.process_message(session, user_message)
        spoken_response = proctor_payload.get("spoken_response", "")
        whiteboard_actions = proctor_payload.get("whiteboard_actions", [])
    elif can_use_local_board:
        spoken_response = ""
        whiteboard_actions = []
        tutor_payload = {"advance_topic": False}
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

    concept_phase_used = False
    if route != "proctor_agent" and action not in {"homework", "finish", "end"}:
        explicit_exercise_action = action in {"next_exercise", "next_pdf_exercise", "refresh_problem", "previous_problem"}
        concept_actions = None
        if not explicit_exercise_action and not input_data.get("answer") and not input_data.get("question"):
            concept_actions = _chapter_teaching_phase_actions(session)

        if concept_actions is not None:
            whiteboard_actions = concept_actions
            concept_phase_used = True
            session.next_problem_actions = []
        else:
            whiteboard_actions = _next_problem_actions_for_session(
                session,
                topic=session.current_topic or session.chapter_name,
                rag_context=rag_context,
                action=action,
            )
            # Prefetch the next problem actions (non-mutating peek) for faster seamless transition
            try:
                if not getattr(session, "next_problem_actions", None):
                    next_actions = _peek_next_problem(session, topic=session.current_topic or session.chapter_name, rag_context=rag_context)
                    if next_actions:
                        session.next_problem_actions = next_actions
            except Exception:
                # Fail-safe: do not break the class flow on prefetch errors
                pass
    else:
        if route != "proctor_agent" and tutor_payload:
            whiteboard_actions = [*whiteboard_actions, *_widget_to_actions(tutor_payload.get("widget"))]
        whiteboard_actions = _prepare_problem_whiteboard_actions(
            topic=session.current_topic or session.chapter_name,
            actions=whiteboard_actions,
            variation=turn_index,
            rag_context=rag_context,
            session_id=session.session_id,
        )

    if route != "proctor_agent" and isinstance(session.chapter_transition, dict):
        transition_spoken_prefix, transition_actions = _chapter_transition_actions(session.chapter_transition)
        session.chapter_transition = None
        session.current_topic = _resolve_session_topic(session)

    if transition_spoken_prefix:
        spoken_response = f"{transition_spoken_prefix} {spoken_response}".strip()

    if transition_actions:
        whiteboard_actions = [*transition_actions, *whiteboard_actions]

    if route != "proctor_agent":
        whiteboard_actions = [
            {"action": "clear"},
            *whiteboard_actions,
        ]

    if not concept_phase_used:
        whiteboard_actions = _ensure_problem_headers(
            session,
            whiteboard_actions,
            fallback_problem_no=str(turn_index + 1),
        )
    include_headers = concept_phase_used or action in {"start", "next_topic", "next_chapter", "skip_topic", "skip_chapter"} or turn_index == 0
    whiteboard_actions = _ensure_board_header_actions(session, whiteboard_actions, include_headers=include_headers)
    steps = _steps_from_actions(whiteboard_actions)
    if not steps:
        fallback_actions = _next_problem_actions_for_session(
            session,
            topic=session.current_topic or session.chapter_name,
            rag_context=rag_context,
            action=action,
        )
        whiteboard_actions = _ensure_board_header_actions(session, fallback_actions, include_headers=include_headers)
        steps = _steps_from_actions(whiteboard_actions)
    session.class_problem_cursor = turn_index + 1
    session.questions_asked = int(getattr(session, "questions_asked", 0)) + 1

    chapter_title = session.chapter_name or session.current_topic or "Current Chapter"
    topic_title = session.current_topic or chapter_title
    spoken_response = (
        _spoken_for_concept_board(steps, topic_title, session.teaching_language)
        if concept_phase_used
        else _spoken_from_steps(spoken_response, steps, topic_title, session.teaching_language)
    )
    forced_prefix = None if concept_phase_used else _force_problem_readout_prefix(steps)
    if forced_prefix:
        lowered_spoken = str(spoken_response or "").lower()
        prompt_anchor = forced_prefix.lower().split("let us read the problem statement:", 1)[-1][:60]
        if "let us read the problem statement" not in lowered_spoken and prompt_anchor.strip() not in lowered_spoken:
            spoken_response = f"{forced_prefix}{spoken_response}".strip()
    spoken_response = _sanitize_for_speech(spoken_response)
    voice_chunks = _voice_chunks_from_steps(spoken_response, steps)
    audio_base64 = None
    if TTS_ENABLED and str(spoken_response or "").strip():
        try:
            audio_bytes = await generate_audio(spoken_response)
            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as error:
            print(f"TTS audio generation failed: {error}")
    highlight_steps = [
        str(step).strip() for step in steps if str(step).strip().lower().startswith("step ")
    ] or steps
    board_problem = None if concept_phase_used else _problem_prompt_from_actions(whiteboard_actions)
    problem_meta = {} if concept_phase_used else _extract_problem_metadata(whiteboard_actions)
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
            "mode": "concept" if concept_phase_used else "exercise",
            "problem": board_problem or None,
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
        "chapter_no": problem_meta.get("chapter_no"),
        "chapter_name": problem_meta.get("chapter_name") or chapter_title,
        "exercise_no": problem_meta.get("exercise_no"),
        "problem_no": problem_meta.get("problem_no"),
        "problem_statement": problem_meta.get("problem_statement") or board_problem or None,
        "session_time_left_seconds": _class_time_left_seconds(session),
        "session_duration_seconds": int(session.class_duration_minutes * 60),
        "session_expired": False,
        "avatar_voice": {
            "style": "calm",
            "pace": "steady",
            "sync_to_whiteboard": True,
            "pause_ms": 180,
        },
        "avatar_stream": {
            "voice_chunks": voice_chunks,
            "steps": highlight_steps,
            "pace": "steady",
            "pause_ms": 180,
        },
        "audio_base64": audio_base64,
    }


@router.post("/ask")
async def tutor_api(req: TutorRequest):
    print("POST /tutor/ask")
    print("REQ:", req)

    try:
        mode = req.mode
        input_data = req.input
        route_as_doubt, chat_question = _should_route_as_doubt(input_data)
        if route_as_doubt:
            mode = "doubt"

        if mode in {"class", "mock_test"}:
            return await _handle_multi_agent_class(req, input_data)

        engine = _get_legacy_engine()
        state = engine._ensure_state(req.session_id)
        state.exam = req.get_exam()
        if route_as_doubt and req.mode == "class":
            class_session = orchestrator.sessions.get(req.session_id)
            _seed_doubt_state_from_class_context(state, class_session, input_data)

        question = chat_question or input_data.get("question")
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
        return {"error": "Your error message here"}
