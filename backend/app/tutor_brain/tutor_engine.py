from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional
from app.services.mistake_engine import analyze_attempt
from app.math.solver import solve_equation
from .curriculum import (
    find_topic_by_message,
    get_chapter_position,
    get_concept,
    get_default_topic_slug,
    get_grade_curriculum,
    get_next_concept,
    get_next_topic,
    get_topic,
    get_topic_concepts,
)
from .lesson_state import LessonState
from app.services.firebase_service import save_homework
from app.services.cbse_exercises import (
    build_exercise_solution,
    get_pdf_chapter_number,
    load_all_pdf_exercises,
    load_chapter_pdf_exercises,
)
from app.services.rag_service import retrieve_context
from app.models.session import SessionPhase
from sympy import symbols, solve
import asyncio
from app.cache.cache_manager import get_cache, set_cache
import random

AI_DOUBT_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-doubt")
CLASS_DURATION_MINUTES = 45


def sanitize_for_speech(text: str) -> str:
    if not text:
        return text
    replacements = {
        "√": " square root of ",
        "sqrt": " square root of ",
        "π": " pi ",
        "×": " times ",
        "÷": " divided by ",
        "°": " degrees ",
        "≤": " less than or equal to ",
        "≥": " greater than or equal to ",
        "≠": " not equal to ",
        "≈": " approximately equal to ",
        "~": " approximately ",
        "^2": " squared ",
        "^3": " cubed ",
        "^": " to the power of ",
    }
    for symbol, word in replacements.items():
        text = text.replace(symbol, word)
    return re.sub(r"\s+", " ", text).strip()

def clean_expression(expr: str) -> str:
    expr = expr.lower()

    # ✅ REMOVE WORDS
    expr = expr.replace("solve:", "").replace("solve", "")

    # ✅ REMOVE ALL KNOWN BAD ENCODINGS
    bad_chars = ["Â", "â", "Ã", "�"]
    for ch in bad_chars:
        expr = expr.replace(ch, "")

    # ✅ NORMALIZE POWERS
    expr = (
        expr
        .replace("x²", "x**2")
        .replace("²", "**2")
        .replace("^", "**")
        .replace(" ", "")
    )

    # ✅ HANDLE =0 CORRECTLY
    if "=0" in expr:
        expr = expr.replace("=0", "")
    elif "=" in expr:
        expr = expr.split("=")[0]

    # ✅ FIX MULTIPLICATION (5x → 5*x)
    
    expr = re.sub(r'(\d)(x)', r'\1*\2', expr)

    return expr
    
def parse_input(ans: str):
    try:
         return sorted([float(x.strip()) for x in ans.split(",")])
    except:
        return None


def _normalize_exam(exam: str | None) -> str:
    return "jee" if (exam or "").lower() == "jee" else "cbse"


def _default_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "correct": 0,
        "wrong": 0,
        "by_mistake": {},
        "by_topic": {},
        "by_pattern": {},
    }


def _answers_match(parsed: list[float], expected: list[float]) -> bool:
    if len(parsed) != len(expected):
        return False
    return all(abs(a - b) <= 1e-6 for a, b in zip(sorted(parsed), sorted(expected)))


def _split_avatar_text(text: str) -> list[str]:
    chunks: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(text or "").strip()):
        words = sentence.split()
        for index in range(0, len(words), 18):
            chunk = " ".join(words[index:index + 18]).strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def format_for_avatar(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "voice_chunks": _split_avatar_text(response.get("voice_text") or response.get("explanation") or ""),
        "steps": response.get("steps") or [],
        "pace": response.get("pace") or "slow",
        "pause_ms": response.get("pause_ms") or 900,
    }


@dataclass
class ClassroomState:
    grade: int = 10
    stage: str = "INTRO"
    topic_slug: str | None = None
    topic_title: str | None = None
    concept_id: str | None = None
    concept_title: str = ""
    current_concept_title: str | None = None
    summary: str = ""
    note_cards: list[str] = field(default_factory=list)
    whiteboard: dict[str, Any] = field(default_factory=dict)
    public_state: dict[str, Any] = field(default_factory=dict)
    current_question_index: int = 0
    active_problem: dict[str, Any] | None = None
    attempts_on_problem: int = 0
    homework: list[str] = field(default_factory=list)
    class_duration_minutes: int = CLASS_DURATION_MINUTES
    chapter_label: str = ""
    exam: str = "cbse"
    active_phase: SessionPhase = SessionPhase.TEACHING
    stats: dict[str, Any] = field(default_factory=_default_stats)
    mistakes: list[str] = field(default_factory=list)
    last_questions: list[str] = field(default_factory=list)
    mistake_count: dict[str, int] = field(default_factory=dict)
    pattern_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    correct_streak: int = 0
    wrong_streak: int = 0
    difficulty: str = "easy"
    current_topic: str | None = None
    current_chapter: str | None = None
    current_concept: str | None = None
    current_chapter_index: int = 0
    current_topic_index: int = 0
    current_concept_index: int = 0
    homework_chapter_index: int | None = None
    homework_topic_index: int | None = None
    homework_concept_index: int | None = None
    curriculum: dict[str, Any] = field(default_factory=dict)
    learning_path: list[dict[str, Any]] = field(default_factory=list)
    class_last_step: str | None = None
    class_phase: str = "teach"
    exam_state: dict[str, Any] = field(default_factory=dict)

    
    concept_steps: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    step_index: int = 0
    waiting_for_student: bool = False
    session_notes: list[str] = field(default_factory=list)
    board_problem_phase: str = "ncert_examples"
    board_problem_index: int = 0
    cbse_outline: dict[str, Any] = field(default_factory=dict)
    completed_exercise_types: list[str] = field(default_factory=list)
    completed_concepts: list[str] = field(default_factory=list)
    current_exercise_type: str | None = None
    pdf_exercise_session: dict[str, Any] = field(default_factory=dict)
    last_doubt_question: str | None = None
    last_doubt_plan: dict[str, Any] = field(default_factory=dict)
    
    def get_weak_area(state):
        stats = getattr(state, "stats", {})
        mistakes = stats.get("by_mistake", {})

        if not mistakes:
            return None

        return max(mistakes, key=mistakes.get)


class PlannerAgent:
    def get_next_step(self, state: ClassroomState) -> dict[str, Any]:
        concepts = get_topic_concepts(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        if not concepts:
            return {"type": "homework", "concept": None}

        index = min(getattr(state, "current_concept_index", 0), len(concepts) - 1)
        concept = concepts[index]
        phase = getattr(state, "class_phase", "teach")

        if phase == "teach":
            return {"type": "teach", "concept": concept, "concept_index": index}
        if phase == "question":
            return {"type": "question", "concept": concept, "concept_index": index}
        if index + 1 < len(concepts):
            state.current_concept_index = index + 1
            state.class_phase = "teach"
            next_concept = concepts[state.current_concept_index]
            return {"type": "teach", "concept": next_concept, "concept_index": state.current_concept_index}
        return {"type": "homework", "concept": concept, "concept_index": index}


class TutorEngine:
    TEACHING_GUARDRAIL_KEYWORDS = ("exercise", "test", "homework", "solution", "practice")
    TEACHING_GUARDRAIL_BLOCK_MESSAGE = (
        "We're focusing on the theory and concepts right now, Mitesh. "
        "Let's master this foundation before moving to practice exercises!"
    )
    PRACTICE_GATE_MESSAGE = "We will reach the exercises once we've completed the theory."

    def __init__(self) -> None:
        self._states: dict[str, ClassroomState] = {}
        self._state_lock = Lock()
        self.planner = PlannerAgent()

    def _is_unauthorized_query(self, session, user_input: str) -> str | None:
        phase = getattr(session, "active_phase", SessionPhase.TEACHING)
        phase_value = str(getattr(phase, "value", phase) or "").strip().lower()
        if phase_value != SessionPhase.TEACHING.value:
            return None

        lowered = str(user_input or "").strip().lower()
        if any(keyword in lowered for keyword in self.TEACHING_GUARDRAIL_KEYWORDS):
            return self.TEACHING_GUARDRAIL_BLOCK_MESSAGE
        return None

    def _phase_value(self, session: ClassroomState) -> str:
        raw_phase = getattr(session, "active_phase", SessionPhase.TEACHING)
        return str(getattr(raw_phase, "value", raw_phase) or SessionPhase.TEACHING.value).strip().lower()

    def _is_practice_phase(self, session: ClassroomState) -> bool:
        return self._phase_value(session) == SessionPhase.PRACTICE.value

    def _set_active_phase(self, session: ClassroomState, phase: SessionPhase) -> None:
        session.active_phase = phase
        # Keep string mirror in sync for compatibility with new session schema.
        if hasattr(session, "current_phase"):
            session.current_phase = phase.value

    def hydrate_session(self, session_id, session) -> None:
        with self._state_lock:
            state = self._states.get(session_id)
            if state is None:
                state = self._fresh_state(getattr(session, "grade", 10), getattr(session, "topic_slug", None))
                self._states[session_id] = state

            state.grade = getattr(session, "grade", state.grade)
            state.active_phase = getattr(session, "active_phase", state.active_phase)
            state.stage = getattr(session, "lesson_stage", state.stage) or state.stage
            if getattr(session, "topic_slug", None):
                self._set_topic(state, session.grade, session.topic_slug, reset=True)
                state.stage = getattr(session, "lesson_stage", state.stage) or state.stage

            metadata = getattr(session, "metadata", {}) or {}
            if isinstance(metadata.get("concept_id"), str):
                concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), metadata["concept_id"])
                if concept:
                    state.concept_id = concept["id"]
                    state.concept_title = concept["title"]
            if isinstance(metadata.get("whiteboard"), dict):
                state.whiteboard = metadata["whiteboard"]
            if isinstance(metadata.get("homework"), list):
                state.homework = [str(item) for item in metadata["homework"][:3]]
            if getattr(session, "lesson_notes", None):
                state.note_cards = list(session.lesson_notes[:6])
            if getattr(session, "summary", None):
                state.summary = session.summary
            state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
            state.active_problem = self._current_problem(state) if state.stage == "PRACTICE" else None
            print("Hydrated classroom state")

    def process(self, session_id: str, message, session_record=None, exam="cbse") -> str:

        state = self._ensure_state(session_id, session_record)
        state.exam = _normalize_exam(getattr(state, "exam", exam) or exam)
        # ✅ HANDLE DICT INPUT HERE (MAIN FIX)
        if isinstance(message, dict):
            answer = message.get("answer")
            question = message.get("question")

            if question:
                state.active_problem = {"prompt": question}

            message = answer

        text = (message or "").strip()
        lowered = text.lower()
        block_message = self._is_unauthorized_query(state, text)
        if block_message:
            return block_message

        # 🔥 STEP FLOW PRIORITY
        
        if "start practice" in lowered or "test me" in lowered:
            state.stage = "PRACTICE"
            state.active_problem = self._current_problem(state)
            state.attempts_on_problem = 0

            return f"Let's test your understanding.\n\n{state.active_problem['prompt']}"

        if "pdf exercise" in lowered or "all exercises" in lowered or "all exercise" in lowered:
            response = self.run_class(
                state,
                {"action": "solve_all_pdf_exercises", "grade": state.grade, "subject": "math"},
            )
            return self._text_from_class_response(response)

        if getattr(state, "class_last_step", None) == "pdf_exercise" and self._looks_like_progress_request(lowered):
            response = self.run_class(state, {"action": "next_pdf_exercise", "grade": state.grade, "subject": "math"})
            return self._text_from_class_response(response)

        if self._is_teaching_phase(state) and self._looks_like_solution_attempt(text):
            return "Let's finish the theory first! I'll guide you through the formula."
        
        if state.stage == "STEP_TEACH":
            return self._next_teaching_step(state, text)

        topic_switch = find_topic_by_message(state.grade, text)
        if topic_switch and topic_switch["slug"] != state.topic_slug:
            self._set_topic(state, state.grade, topic_switch["slug"], reset=True)
            return self._build_topic_switch_response(state)

        concept = self._concept_for_message(state, lowered)
        if concept and concept["id"] != state.concept_id:
            state.concept_id = concept["id"]
            state.concept_title = concept["title"]
            state.current_question_index = 0
            state.active_problem = None
            state.stage = "TEACH"
            return self._teach_current_concept(state, transition=True)

        if self._should_treat_as_answer(state, lowered):
            return self._handle_answer(state, text)

        if self._looks_like_progress_request(lowered):
            return self._advance(state)

        return self._answer_like_teacher(state, text)

    def snapshot(self, session_id) -> LessonState:
        state = self._ensure_state(session_id, None)
        return LessonState(
            stage=state.stage,
            topic_slug=state.topic_slug,
            topic_title=state.topic_title,
            summary=state.summary,
            note_cards=list(state.note_cards),
            concept_id=state.concept_id,
            concept_title=state.concept_title,
            messages=[],
            whiteboard=dict(state.whiteboard),
            current_question_index=state.current_question_index,
            homework=list(state.homework),
            class_duration_minutes=state.class_duration_minutes,
            chapter_label=state.chapter_label,
        )

    def generate_response(self, message: str, state: Optional[LessonState] = None) -> str:
        return self.process("stateless", message)

    def _ensure_state(self, session_id: str, session_record=None) -> ClassroomState:
        with self._state_lock:
            state = self._states.get(session_id)
            if state is not None:
                if session_record is not None:
                    state.grade = getattr(session_record, "grade", state.grade)
                    state.active_phase = getattr(session_record, "active_phase", state.active_phase)
                return state

            grade = getattr(session_record, "grade", 10) if session_record is not None else 10
            topic_slug = getattr(session_record, "topic_slug", None) if session_record is not None else None
            state = self._fresh_state(grade, topic_slug)
            if session_record is not None:
                state.active_phase = getattr(session_record, "active_phase", state.active_phase)
            self._states[session_id] = state
            return state

    def _fresh_state(self, grade: int, topic_slug: str | None) -> ClassroomState:
        topic = get_topic(grade, topic_slug or get_default_topic_slug(grade))
        concept = get_concept(grade, topic["slug"] if topic else get_default_topic_slug(grade))
        state = ClassroomState(
            grade=grade,
            topic_slug=topic["slug"] if topic else topic_slug or get_default_topic_slug(grade),
            topic_title=topic["title"] if topic else "CBSE Mathematics",
            concept_id=concept["id"] if concept else None,
            concept_title=concept["title"] if concept else "",
            chapter_label=self._chapter_label(grade, topic["slug"] if topic else topic_slug),
            current_chapter=(topic["title"] if topic else "CBSE Mathematics"),
        )
        self._refresh_public_state(state, include_problem=False)
        return state

    def _set_topic(self, state: ClassroomState, grade: int, topic_slug: str, reset: bool) -> None:
        topic = get_topic(grade, topic_slug)
        concept = get_concept(grade, topic_slug)
        state.grade = grade
        state.topic_slug = topic_slug
        state.topic_title = topic["title"] if topic else topic_slug.replace("_", " ").title()
        state.current_chapter = state.topic_title
        state.concept_id = concept["id"] if concept else None
        state.concept_title = concept["title"] if concept else ""
        state.chapter_label = self._chapter_label(grade, topic_slug)
        if reset:
            state.stage = "INTRO"
            state.current_question_index = 0
            state.active_problem = None
            state.attempts_on_problem = 0
        self._refresh_public_state(state, include_problem=False)

    def _chapter_label(self, grade: int, topic_slug: str | None) -> str:
        chapter_number, total = get_chapter_position(grade, topic_slug)
        return f"Chapter {chapter_number} of {total}"

    def _build_homework(self, topic: dict | None, concept: dict | None) -> list[str]:
        tasks: list[str] = []
        if concept:
            tasks.extend(item.strip() for item in concept.get("homework", []) if item and item.strip())
        if topic:
            tasks.extend(item.strip() for item in topic.get("homework", []) if item and item.strip())
        deduped = [task for task in dict.fromkeys(tasks) if task]
        return deduped[:3]

    def _important_memory_note(self, topic: dict | None, concept: dict | None) -> str | None:
        if concept and concept.get("definition"):
            return (
                f"Important: remember this definition. It is often useful in CBSE questions. "
                f"{concept['definition']}"
            )

        concept_title = (concept.get("title", "") if concept else "").lower()
        for keyword in ("theorem", "lemma", "formula", "identity", "rule", "algorithm"):
            if keyword in concept_title:
                anchor = (
                    (concept.get("board_work", [None])[0] if concept else None)
                    or (topic.get("teaching_anchor") if topic else None)
                )
                if anchor:
                    return (
                        f"Important: remember this {keyword}. It is often needed in CBSE questions. "
                        f"{anchor}"
                    )

        if topic and topic.get("teaching_anchor"):
            return (
                f"Important: keep this in mind. It often helps in CBSE questions. "
                f"{topic['teaching_anchor']}"
            )

        return None

    def _write_problem_on_board(self, state: ClassroomState, problem: dict[str, Any]) -> None:
        steps = [str(step).strip() for step in problem.get("steps", []) if str(step).strip()]
        answer_text = self._format_expected_answer(problem)

        chalk_lines = list(state.whiteboard.get("chalk_lines", []))
        equations = list(state.whiteboard.get("equations", []))

        for step in steps[:3]:
            if "=" in step:
                equations.append(step)
            else:
                chalk_lines.append(step)

        if problem.get("answer_type") == "pair":
            equations.append(answer_text)
        else:
            chalk_lines.append(f"Answer: {answer_text}")

        state.whiteboard["chalk_lines"] = [
            line for line in dict.fromkeys(item for item in chalk_lines if item)
        ][:6]
        state.whiteboard["equations"] = [
            line for line in dict.fromkeys(item for item in equations if item)
        ][:5]

    def _problem_method_note(self, topic: dict | None, concept: dict | None, problem: dict[str, Any]) -> str | None:
        theorem_used = problem.get("theorem_used")
        if isinstance(theorem_used, str) and theorem_used.strip():
            return f"Theorem used: {theorem_used.strip()}."

        rule_used = problem.get("rule_used")
        if isinstance(rule_used, str) and rule_used.strip():
            return f"Rule used: {rule_used.strip()}."

        method = problem.get("method")
        if isinstance(method, str) and method.strip():
            return f"Method used: {method.strip()}."

        if concept and concept.get("definition"):
            return f"Key idea used: {concept['definition']}"

        if topic and topic.get("teaching_anchor"):
            return f"Key idea used: {topic['teaching_anchor']}"

        return None

    def _format_list(self, items: list[str]) -> str:
        return "\n".join(f"{index + 1}. {item}" for index, item in enumerate(items))

    def _looks_like_progress_request(self, lowered: str) -> bool:
        normalized = re.sub(r"[^a-z0-9\s]", " ", lowered.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return False

        exact_requests = {
            "ready",
            "rady",
            "redy",
            "redi",
            "start",
            "stert",
            "begin",
            "bigin",
            "continue",
            "continew",
            "next",
            "nex",
            "nekst",
            "go on",
            "lets start",
            "let us start",
            "start class",
            "start lesson",
            "start chapter",
            "next topic",
            "next concept",
            "teach from basics",
        }
        if normalized in exact_requests:
            return True

        tokens = normalized.split()
        return any(
            token
            in {
                "ready",
                "rady",
                "redy",
                "redi",
                "start",
                "stert",
                "begin",
                "bigin",
                "continue",
                "continew",
                "next",
                "nex",
                "nekst",
            }
            for token in tokens
        )

    def _concept_problem_sets(self, concept: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        textbook_examples = [
            problem
            for problem in concept.get("ncert_examples", [])
            if isinstance(problem, dict)
        ]
        exercise_problems = [
            problem
            for problem in concept.get("exercise_problems", [])
            if isinstance(problem, dict)
        ]

        if not textbook_examples:
            textbook_examples = [
                problem
                for problem in concept.get("practice_problems", [])
                if isinstance(problem, dict)
            ]

        return textbook_examples[:4], exercise_problems[:3]

    def _append_problem_walkthrough(
        self,
        *,
        state: ClassroomState,
        topic: dict[str, Any],
        concept: dict[str, Any],
        label: str,
        problems: list[dict[str, Any]],
        parts: list[str],
    ) -> None:
        for index, problem in enumerate(problems, start=1):
            steps = [str(step).strip() for step in problem.get("steps", []) if str(step).strip()]
            if steps:
                state.note_cards = list(dict.fromkeys([*state.note_cards, *steps]))[:6]
            self._write_problem_on_board(state, problem)
            parts.append(f"{label} {index}: {problem['prompt']}")
            method_note = self._problem_method_note(topic, concept, problem)
            if method_note:
                parts.append(method_note)
            parts.extend(
                f"Step {step_index + 1}: {step}"
                for step_index, step in enumerate(steps)
            )
            parts.append(f"So the answer is {self._format_expected_answer(problem)}.")

    def _build_wrap_response(self, state: ClassroomState, answer_text: str | None = None) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        next_topic = get_next_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))

        state.stage = "WRAP"
        state.active_problem = None
        state.attempts_on_problem = 0
        self._refresh_public_state(state, include_problem=False)

        parts: list[str] = []
        if answer_text:
            parts.append(f"Good. That is correct: {answer_text}.")

        topic_title = topic["title"] if topic else state.topic_title or "the current chapter"
        parts.append(
            f"That completes today's **{CLASS_DURATION_MINUTES}-minute class** for "
            f"{state.chapter_label}: **{topic_title}**."
        )
        parts.append(
            "We covered the chapter in sequence, wrote the key board points, and solved the work step by step."
        )

        if state.homework:
            parts.append(
                "Homework for today:\n"
                + self._format_list(state.homework)
                + "\n\nYou can open it again in the Homework tab."
            )

        if next_topic:
            next_label = self._chapter_label(state.grade, next_topic["slug"])
            parts.append(
                f"In the next class, we will move to {next_label}: **{next_topic['title']}**."
            )
        else:
            parts.append("You have reached the end of the chapter list, so the next class can be revision or mixed practice.")

        return "\n\n".join(parts)

    def _advance(self, state: ClassroomState) -> str:
        if state.stage == "WRAP":
            next_topic = get_next_topic(
                state.grade,
                state.topic_slug or get_default_topic_slug(state.grade),
            )
            if not next_topic:
                state.summary = "Completed the full chapter order for this class."
                return (
                    "We have completed the chapter sequence for this grade.\n\n"
                    "If you want, I can revise any chapter or give mixed revision practice."
                )

            self._set_topic(state, state.grade, next_topic["slug"], reset=True)
            announcement = (
                f"Good. We are starting the next {CLASS_DURATION_MINUTES}-minute class.\n\n"
                f"{self._chapter_label(state.grade, next_topic['slug'])}: **{next_topic['title']}**.\n\n"
            )
            return announcement + self._teach_current_concept(state, transition=False)

        if state.stage == "INTRO":
            return self._teach_current_concept(state, transition=False)
        
        if state.stage == "PRACTICE" and state.active_problem:
            return self._restate_problem(state)

        next_concept = get_next_concept(
            state.grade,
            state.topic_slug or get_default_topic_slug(state.grade),
            state.concept_id,
        )
        if next_concept and next_concept["id"] != state.concept_id:
            state.concept_id = next_concept["id"]
            state.concept_title = next_concept["title"]
            state.current_question_index = 0
            state.active_problem = None
            state.attempts_on_problem = 0
            state.stage = "TEACH"
            self._refresh_public_state(state, include_problem=False)
            return self._teach_current_concept(state, transition=True)

        return self._build_wrap_response(state)

    def _build_intro(self, state: ClassroomState) -> str:
        # Ensure we are in teaching mode
        state.stage = "STEP_TEACH"
        self._set_active_phase(state, SessionPhase.TEACHING)

        # Directly start teaching (no intro text blocking flow)
        return self._teach_current_concept(state, transition=False)

    def _build_topic_switch_response(self, state: ClassroomState) -> str:
        return (
            f"Sure.\n\n"
            f"Chapter: **{state.topic_title}**\n"
            f"Topic: **{state.concept_title or 'First topic'}**\n\n"
            "We will take the topic in order, solve the textbook examples first, then exercise problems on the whiteboard, and save the remaining homework for later revision.\n\n"
            "Try a question to check your understanding"
        )

    def _teach_current_concept(self, state: ClassroomState, transition: bool) -> str:
        topic = get_topic(state.grade, state.topic_slug)
        concept = get_concept(state.grade, state.topic_slug, state.concept_id)
        if concept:
            state.current_concept_title = concept.get("title")

        if not topic or not concept:
            return "Tell me the chapter name."
        
        state.current_concept_title = concept["title"]
        state.stage = "TEACH"

        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        rag_text = self._get_cbse_context(concept["title"], state) if exam == "cbse" else concept["title"]

        if rag_text:
            try:
                                
                plan = self._run_lesson_plan(rag_text, exam=exam)

                state.concept_steps = plan["concept_steps"]
                state.examples = plan.get("examples", [])
                state.homework = ["Practice 2 questions from this concept"]

                state.stage = "STEP_TEACH"
                state.step_index = 0
                state.waiting_for_student = False

                return (
                    f"Chapter: {topic['title']}\n"
                    f"Topic: {concept['title']}\n\n"
                    "We will learn step by step.\n\n"
                    "Say 'ready' to start."
                )
            except Exception as e:
                print("Planner failed:", e)

        return concept.get("explanation", "")

    def _offer_practice(self, state: ClassroomState) -> str:
        if state.active_problem is None:
            return (
                "I have already explained this topic and solved the textbook and exercise questions on the board.\n\n"
                "Read the whiteboard, copy the steps, and say **next** when you are ready for the next topic.\n\n"
                "You can also ask for **homework** any time."
            )
        state.stage = "PRACTICE"
        self._set_active_phase(state, SessionPhase.PRACTICE)
        self._refresh_public_state(state, include_problem=True)
        return self._restate_problem(state)

    def _restate_problem(self, state: ClassroomState) -> str:
        if not state.active_problem:
            return "I do not have a class question ready yet. Say ready, and I will start a guided example first."
        hint = state.active_problem.get("hint")
        parts = ["Your turn now.", state.active_problem["prompt"]]
        if hint and state.attempts_on_problem > 0:
            parts.append(f"Hint: {hint}")
        parts.append("Give only the answer first. If you want, you can also ask for a hint or a full board solution.")
        return "\n\n".join(parts)
          
    def _handle_answer(self, state, message):
        if isinstance(message, dict):
            question = message.get("question")
            if question:
                state.active_problem = {"prompt": question}
            message = message.get("answer")

        if not message:
            return {
                "correct": False,
                "mistake_type": "format_error",
                "hint": "Please provide an answer like 2,3",
                "explanation": "Answer is missing",
                "steps": [],
                "shortcut": None,
                "speed_hint": None,
                "adaptive_hint": None,
                "next_question": None,
            }

        problem = getattr(state, "active_problem", None)
        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        state.exam = exam

        if not problem:
            return {
                "correct": False,
                "mistake_type": "system_error",
                "hint": None,
                "explanation": "No active problem",
                "steps": [],
                "shortcut": None,
                "speed_hint": None,
                "adaptive_hint": None,
                "next_question": None,
            }

        try:
            expr = clean_expression(problem.get("prompt", ""))
            x = symbols("x")
            expected = sorted(float(s.evalf()) for s in solve(expr, x) if s.is_real)
            parsed = parse_input(str(message))

            if not parsed:
                return {
                    "correct": False,
                    "mistake_type": "format_error",
                    "hint": "Use comma like 2,3",
                    "explanation": "Invalid format",
                    "steps": [],
                    "shortcut": None,
                    "speed_hint": None,
                    "adaptive_hint": None,
                    "next_question": None,
                }

            if exam == "jee":
                problem.setdefault("topic", "quadratic")
                problem.setdefault("pattern", self._classify_jee_pattern(problem.get("prompt", "")))
                problem.setdefault("difficulty", getattr(state, "difficulty", "easy"))

            topic = problem.get("topic") or "quadratic"
            pattern = problem.get("pattern") or self._classify_jee_pattern(problem.get("prompt", ""))
            state.correct_count = getattr(state, "correct_count", 0)
            state.wrong_count = getattr(state, "wrong_count", 0)
            state.stats = getattr(state, "stats", _default_stats())
            state.stats.setdefault("total", 0)
            state.stats.setdefault("correct", 0)
            state.stats.setdefault("wrong", 0)
            state.stats.setdefault("by_mistake", {})
            state.stats.setdefault("by_topic", {})
            state.stats.setdefault("by_pattern", {})
            state.stats["by_topic"].setdefault(topic, {"correct": 0, "wrong": 0})
            state.stats["by_pattern"].setdefault(pattern, {"correct": 0, "wrong": 0})
            state.stats["total"] += 1

            is_correct = _answers_match(parsed, expected)
            if is_correct:
                state.correct_count += 1
                state.stats["correct"] += 1
                state.stats["by_topic"][topic]["correct"] += 1
                state.stats["by_pattern"][pattern]["correct"] += 1
                if exam == "jee":
                    self._update_jee_performance(state, pattern, True)
                    next_problem = self._next_jee_question(state)
                else:
                    next_problem = self._next_adaptive_problem(state)
                return {
                    "correct": True,
                    "mistake_type": None,
                    "hint": None,
                    "explanation": "Correct answer" if exam == "jee" else "Correct. Your answer matches the solved roots.",
                    "steps": [],
                    "shortcut": "Substitute roots back into the equation." if exam == "jee" else None,
                    "speed_hint": self._speed_hint(exam, None),
                    "adaptive_hint": None,
                    "next_question": self._format_next_question(exam, next_problem),
                }

            if len(parsed) < len(expected):
                mistake_type = "missing_root"
            elif len(parsed) == len(expected):
                if any(x not in expected for x in parsed):
                    mistake_type = "concept_error"
                else:
                    mistake_type = "sign_error"
            else:
                mistake_type = "concept_error"

            state.wrong_count += 1
            state.stats["wrong"] += 1
            state.stats["by_topic"][topic]["wrong"] += 1
            state.stats["by_pattern"][pattern]["wrong"] += 1
            state.stats["by_mistake"][mistake_type] = state.stats["by_mistake"].get(mistake_type, 0) + 1
            state.mistakes = getattr(state, "mistakes", [])
            state.mistakes.append(mistake_type)

            state.mistake_count = getattr(state, "mistake_count", {})
            count_key = pattern if exam == "jee" else mistake_type
            count = state.mistake_count.get(count_key, 0) + 1
            state.mistake_count[count_key] = count
            if count == 1:
                adaptive_hint = "Try again carefully."
            elif count == 2:
                adaptive_hint = "You're repeating the same mistake."
            else:
                adaptive_hint = "Stop and rethink the concept."

            if exam == "jee":
                self._update_jee_performance(state, pattern, False)
                plan = self._build_jee_response(problem, mistake_type)
                next_problem = self._next_jee_question(state)
                return {
                    "correct": False,
                    "mistake_type": mistake_type,
                    "hint": plan.get("mistake_explanation"),
                    "explanation": plan.get("mistake_explanation"),
                    "steps": plan.get("concept_steps", []),
                    "shortcut": plan.get("shortcut"),
                    "speed_hint": plan.get("speed_hint"),
                    "adaptive_hint": adaptive_hint,
                    "next_question": self._format_next_question(exam, next_problem),
                }

            cache_key = f"{exam}|{problem.get('prompt','').strip()}|{str(message).strip()}|{mistake_type}"
            cached = get_cache(cache_key)
            if cached:
                next_problem = self._next_adaptive_problem(state)
                cached["next_question"] = self._format_next_question(exam, next_problem)
                return cached

            planner_context = self._get_cbse_context(problem.get("prompt", ""), state) or problem.get("prompt", "")
            plan = self._run_lesson_plan(planner_context, mistake_type, exam)
            next_problem = self._next_adaptive_problem(state)
            result = {
                "correct": False,
                "mistake_type": mistake_type,
                "hint": plan.get("mistake_explanation"),
                "explanation": plan.get("mistake_explanation"),
                "steps": plan.get("concept_steps", []),
                "shortcut": plan.get("shortcut"),
                "speed_hint": None,
                "adaptive_hint": adaptive_hint,
                "next_question": self._format_next_question(exam, next_problem),
            }
            set_cache(cache_key, result)
            return result

        except Exception as e:
            print("ERROR:", e)
            return {
                "correct": False,
                "mistake_type": "system_error",
                "hint": None,
                "explanation": "Error evaluating",
                "steps": [],
                "shortcut": None,
                "speed_hint": None,
                "adaptive_hint": None,
                "next_question": None,
            }
            
    def _handle_correct_answer(self, state: ClassroomState) -> str:
            problem = state.active_problem
            concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
            if not problem or not concept:
                return "Good. That is correct."

            answer_text = self._format_expected_answer(problem)
            practice_problems = concept.get("practice_problems", [])
            if state.current_question_index + 1 < len(practice_problems):
                state.current_question_index += 1
                state.active_problem = practice_problems[state.current_question_index]
                state.attempts_on_problem = 0
                state.stage = "PRACTICE"
                self._refresh_public_state(state, include_problem=True)
                return (
                    f"Good. That is correct: {answer_text}.\n\n"
                    f"Now try the next NCERT question.\n\n{state.active_problem['prompt']}"
                )

            next_concept = get_next_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
            if next_concept:
                state.concept_id = next_concept["id"]
                state.concept_title = next_concept["title"]
                state.current_question_index = 0
                state.active_problem = None
                state.attempts_on_problem = 0
                state.stage = "TEACH"
                self._refresh_public_state(state, include_problem=False)
                return f"Good. That is correct: {answer_text}.\n\nYou understood this part, so let us move ahead.\n\n{self._teach_current_concept(state, transition=True)}"

            return self._build_wrap_response(state, answer_text=answer_text)

    def _give_hint(self, state: ClassroomState) -> str:
        if not state.active_problem:
            return "Ask me to start a practice question first."

        state.attempts_on_problem += 1
        self._refresh_public_state(state, include_problem=True)

        hint = state.active_problem.get("hint") or "Think step-by-step"

        return f"Hint: {hint}\n\nTry again: {state.active_problem['prompt']}"

    def _next_teaching_step(self, state: ClassroomState, user_input=None):

        # WAIT
        if state.waiting_for_student:
            if user_input and user_input.lower() in ["ready", "done", "yes", "ok"]:
                state.waiting_for_student = False
            else:
                # 🔥 DON'T BLOCK FLOW
                state.waiting_for_student = False

        # STEP
        if state.step_index < len(state.concept_steps):
            step = state.concept_steps[state.step_index]
            state.step_index += 1
            state.waiting_for_student = True

            # WHITEBOARD WRITE
            state.whiteboard["chalk_lines"] = [step]

            return f"{step}\n\n(write this and say 'ready')"

        # EXAMPLE
        if state.examples:
            ex = state.examples.pop(0)
            state.waiting_for_student = True

            state.whiteboard["chalk_lines"] = [ex]

            return f"Example:\n\n{ex}"

        # HOMEWORK
        if state.homework:
            state.stage = "HOMEWORK"
            return "Homework:\n\n" + "\n".join(state.homework)

        state.stage = "PRACTICE"

        # 🔥 Set first problem
        state.active_problem = self._current_problem(state)
        state.attempts_on_problem = 0

        return f"Now let's try a question:\n\n{state.active_problem['prompt']}"
        

    def _give_homework(self, state: ClassroomState) -> str:
        if not self._is_practice_phase(state):
            return self.PRACTICE_GATE_MESSAGE

        if not state.homework:
            self._refresh_public_state(state, include_problem=state.active_problem is not None)

        # ✅ Generate + save homework (NEW)
        try:
            session_id = "live-session"
            student_id = "student-1"
            self._generate_rag_homework(state, session_id, student_id)
        except Exception as e:
            print("Homework generation failed:", e)

        if not state.homework:
            return "I do not have homework ready yet. Let me finish this topic first."

        return (
            "Here is your homework.\n\n"
            f"{self._format_list(state.homework)}\n\n"
            "You can reopen it in the Homework tab."
        )

    def _show_solution(self, state: ClassroomState) -> str:
        problem = state.active_problem
        if not problem:
            return "There is no active class question right now."

        steps = problem.get("steps") or ["Solve the equation step by step."]
        answer_text = self._format_expected_answer(problem)
        state.note_cards = list(dict.fromkeys([*state.note_cards, *steps]))[:6]
        self._write_problem_on_board(state, problem)

        response = "Let us solve it on the whiteboard.\n\n"
        response += "\n".join(f"Step {index + 1}: {step}" for index, step in enumerate(steps))
        response += f"\n\nSo the answer is {answer_text}."
        return response + "\n\n" + self._after_solution(state)

    def _after_solution(self, state: ClassroomState) -> str:
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if not concept:
            return "If you want, I can give you another question."

        practice_problems = concept.get("practice_problems", [])
        if state.current_question_index + 1 < len(practice_problems):
            state.current_question_index += 1
            state.active_problem = practice_problems[state.current_question_index]
            state.attempts_on_problem = 0
            state.stage = "PRACTICE"
            self._refresh_public_state(state, include_problem=True)
            return f"Now try the next one by yourself: {state.active_problem['prompt']}"

        next_concept = get_next_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if next_concept:
            state.concept_id = next_concept["id"]
            state.concept_title = next_concept["title"]
            state.current_question_index = 0
            state.active_problem = None
            state.attempts_on_problem = 0
            state.stage = "TEACH"
            self._refresh_public_state(state, include_problem=False)
            return self._teach_current_concept(state, transition=True)

        return self._build_wrap_response(state)

    def _answer_like_teacher(self, state: ClassroomState, message: str) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        support = self._supporting_ncert_point(message, state)
        state.stage = "TEACH"
        self._refresh_public_state(state, include_problem=state.active_problem is not None)

        parts = []
        if concept:
            parts.append(f"Chapter: **{topic['title'] if topic else state.topic_title or 'Current chapter'}**")
            parts.append(f"Topic: **{concept['title']}**")
            parts.append(concept.get("explanation", ""))
            importance_note = self._important_memory_note(topic, concept)
            if importance_note:
                parts.append(importance_note)
            board_work = concept.get("board_work", [])
            if board_work:
                parts.append(f"On the whiteboard, keep this in mind: {board_work[0]}")
        elif topic:
            parts.append(topic.get("summary", "We will build the idea from the chapter basics."))
        if support:
            parts.append(f"A textbook point to remember here is: {support}")
        if state.stage == "PRACTICE" and state.active_problem:
            parts.append(f"Now come to this NCERT question: {state.active_problem['prompt']}")
        else:
            parts.append("If you are ready, say **next** and I will continue the chapter in order.")
        return "\n\n".join(part for part in parts if part)

    def _concept_for_message(self, state: ClassroomState, lowered: str) -> dict | None:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        if not topic:
            return None
        for concept in topic.get("concepts", []):
            fields = [
                concept.get("title", "").lower(),
                concept.get("id", "").replace("_", " ").lower(),
            ]
            if any(field and field in lowered for field in fields):
                return concept
        return None

    def _should_treat_as_answer(self, state: ClassroomState, lowered: str) -> bool:
        if state.active_problem is None:
            return False
        if state.stage != "PRACTICE" or state.active_problem is None:
            return False
        if any(token in lowered for token in ["why", "how", "hint", "explain", "teach", "what", "solution", "steps"]):
            return False
        return self._parse_answer(state.active_problem, lowered) is not None

    def _parse_answer(self, problem: dict[str, Any], raw_message: str):
        answer_type = problem.get("answer_type")
        numbers = re.findall(r"-?\d+(?:\.\d+)?", raw_message)
        if answer_type == "number":
            return float(numbers[0]) if numbers else None
        
        if answer_type == "pair":
            try:
                # 🔥 convert "2,3" → [2.0, 3.0]
                parts = raw_message.replace(" ", "").split(",")

                if len(parts) != 2:
                    return None

                return [float(parts[0]), float(parts[1])]

            except:
                return None

        if answer_type == "text":
            letters = re.sub(r"[^a-z]", "", raw_message.lower())
            return letters or None
        
        return raw_message.strip().lower() or None

    def _is_teaching_phase(self, state: ClassroomState) -> bool:
        stage_value = str(getattr(state, "stage", "") or "").strip().upper()
        class_phase = str(getattr(state, "class_phase", "") or "").strip().lower()
        return stage_value == "TEACH" or class_phase in {"teach", "teaching"}

    def _looks_like_solution_attempt(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered:
            return False

        # Ignore explicit teaching/progression intents.
        if any(token in lowered for token in ["next", "explain", "why", "how", "hint", "teach", "theory"]):
            return False

        if re.search(r"\banswer\s*(is|=)\b", lowered):
            return True
        if re.search(r"\b[a-z]\s*=", lowered):
            return True
        if re.search(r"\d", lowered) and re.search(r"[=+\-*/^]", lowered):
            return True
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:\s*,\s*[-+]?\d+(?:\.\d+)?)*", lowered):
            return True
        return False
    
    
    def _format_expected_answer(self, problem: dict[str, Any]) -> str:
        if problem.get("answer") is not None:
            answer = problem.get("answer")
            labels = problem.get("answer_labels") or []
            if isinstance(answer, list):
                if labels and len(labels) == len(answer):
                    return ", ".join(f"{label} = {value}" for label, value in zip(labels, answer))
                return ", ".join(str(item) for item in answer)
            return str(answer)
        try:
            expr = clean_expression(problem.get("prompt", ""))
            x = symbols("x")
            solutions = solve(expr, x)

            expected = sorted([
                float(s.evalf())
                for s in solutions if s.is_real
            ])

            return ", ".join(str(x) for x in expected)

        except Exception:
            return "Solution not available"

    def _current_problem(self, state: ClassroomState) -> dict[str, Any] | None:
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if not concept or not concept.get("practice_problems"):
            return None
        index = min(state.current_question_index, len(concept["practice_problems"]) - 1)
        return concept["practice_problems"][index]
    
    def _run_lesson_plan(self, context: str, mistake_type: str | None = None, exam: str = "cbse") -> dict[str, Any]:
        cache_key = f"lesson_plan|{exam}|{mistake_type or ''}|{context[:300]}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        try:
            from .lesson_planner import build_lesson_plan

            async def _with_timeout():
                return await asyncio.wait_for(build_lesson_plan(context, mistake_type, exam=exam), timeout=8)

            plan = asyncio.run(_with_timeout())
            set_cache(cache_key, plan)
            return plan
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                plan = loop.run_until_complete(asyncio.wait_for(build_lesson_plan(context, mistake_type, exam=exam), timeout=8))
                set_cache(cache_key, plan)
                return plan
            except Exception:
                return self._fallback_plan(mistake_type, exam)
        except Exception:
            return self._fallback_plan(mistake_type, exam)

    def _fallback_plan(self, mistake_type: str | None = None, exam: str = "cbse") -> dict[str, Any]:
        if _normalize_exam(exam) == "jee":
            return self._build_jee_response({"prompt": "", "pattern": "quadratic_formula"}, mistake_type or "concept_error")
        return {
            "concept_steps": [
                "Read what is given.",
                "Write the main idea in your own words.",
                "Use one small example to check the idea.",
            ],
            "mistake_explanation": "Let us slow down and understand the idea first.",
            "shortcut": None,
            "speed_hint": None,
        }

    def _sentence(self, text: Any) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        return cleaned

    def _get_cbse_chapter_outline(self, topic: dict[str, Any] | str | None, state: ClassroomState) -> dict[str, Any]:
        title = topic.get("title") if isinstance(topic, dict) else str(topic or "")
        slug = topic.get("slug") if isinstance(topic, dict) else None
        cache_key = f"cbse_outline|{title}|{slug or ''}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        context = self._get_cbse_context(
            f"NCERT Class 10 Maths {title} section headings examples exercises types",
            state,
        )
        lines = [self._sentence(line) for line in re.split(r"[\n\r]+", context) if self._sentence(line)]
        heading_pattern = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?([A-Z][A-Za-z0-9 ,:'()/-]{4,80})$")
        example_pattern = re.compile(r"\b(example|illustration)\s*\d*", re.IGNORECASE)
        exercise_pattern = re.compile(r"\b(exercise|question|find|solve|prove|show|verify|construct|draw)\b", re.IGNORECASE)

        sections: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in lines[:120]:
            if heading_pattern.match(line) and not example_pattern.search(line) and len(line.split()) <= 10:
                current = {"title": line, "concepts": [], "examples": [], "exercise_types": []}
                sections.append(current)
                continue
            if current is None:
                current = {"title": title or "Chapter", "concepts": [], "examples": [], "exercise_types": []}
                sections.append(current)
            if example_pattern.search(line):
                current["examples"].append(line[:180])
            elif exercise_pattern.search(line):
                current["exercise_types"].append(line[:180])
            elif len(line.split()) <= 16:
                current["concepts"].append(line[:120])

        if isinstance(topic, dict):
            concepts = topic.get("concepts") or get_topic_concepts(10, topic.get("slug") or "")
        else:
            concepts = []
        if not sections:
            sections = [{"title": title or "Chapter", "concepts": [], "examples": [], "exercise_types": []}]
        for concept in concepts:
            if not isinstance(concept, dict):
                continue
            section = sections[0]
            if concept.get("title"):
                section["concepts"].append(concept["title"])
            section["examples"].extend(
                problem.get("prompt", "")
                for problem in concept.get("ncert_examples", [])
                if isinstance(problem, dict)
            )
            section["exercise_types"].extend(
                problem.get("type") or problem.get("prompt", "")
                for problem in concept.get("exercise_problems", [])
                if isinstance(problem, dict)
            )

        for section in sections:
            for key in ("concepts", "examples", "exercise_types"):
                section[key] = [item for item in dict.fromkeys(self._sentence(x) for x in section[key] if self._sentence(x))][:8]

        outline = {"sections": sections[:8]}
        set_cache(cache_key, outline)
        return outline

    def _concept_analogy(self, concept: dict[str, Any]) -> str:
        title = (concept.get("title") or "").lower()
        if "hcf" in title or "euclid" in title or "division" in title:
            return "Think of packing laddus into equal boxes. The biggest equal box size that leaves no laddus outside is like the HCF."
        if "quadratic" in title or "factor" in title:
            return "Think of opening a locked box with two keys. A quadratic often needs two values that work together."
        if "linear" in title:
            return "Think of a balance scale. Whatever we do on one side, we must do on the other side too."
        if "graph" in title:
            return "Think of a map. Each ordered pair tells us one exact place on the map."
        return "Think of learning a new game rule. First we understand the rule, then we use it in a small example."

    def _generate_cbse_check_question(self, concept: dict[str, Any]) -> dict[str, Any]:
        examples = [
            problem for key in ("practice_problems", "exercise_problems", "ncert_examples")
            for problem in concept.get(key, [])
            if isinstance(problem, dict) and problem.get("prompt")
        ]
        source = examples[0] if examples else {}
        prompt = source.get("prompt", "")
        generated = dict(source)

        quadratic = re.search(r"x\^?2\s*([-+])\s*(\d+)x\s*([-+])\s*(\d+)", prompt.replace("²", "^2"))
        if quadratic:
            b = int(quadratic.group(2))
            c = int(quadratic.group(4))
            if quadratic.group(1) == "-":
                roots_sum = b + 2
                root_a, root_b = 2, max(3, roots_sum - 2)
                generated.update({
                    "prompt": f"Solve x^2 - {root_a + root_b}x + {root_a * root_b} = 0.",
                    "answer_type": "roots",
                    "answer": [root_a, root_b],
                    "accepted_answers": [f"{root_a},{root_b}", f"{root_b},{root_a}"],
                    "steps": [
                        f"Find two numbers whose sum is {root_a + root_b}.",
                        f"The numbers are {root_a} and {root_b}.",
                        f"So the roots are {root_a} and {root_b}.",
                    ],
                })
                generated["difficulty"] = "easy"
                generated["source"] = "cbse_mini_check"
                generated["hint"] = "Find two numbers using sum and product."
                return generated

        difference = re.search(r"x\^?2\s*-\s*(\d+)\s*=\s*0", prompt.replace("²", "^2"))
        if difference:
            generated.update({
                "prompt": "Solve x^2 - 9 = 0.",
                "answer_type": "roots",
                "answer": [-3, 3],
                "accepted_answers": ["-3,3", "3,-3"],
                "steps": [
                    "Move 9 to the other side.",
                    "Take square root on both sides.",
                    "Write both roots: -3 and 3.",
                ],
                "hint": "Remember both plus and minus roots.",
            })
            generated["difficulty"] = "easy"
            generated["source"] = "cbse_mini_check"
            return generated

        division_lemma = re.search(r"write\s+(\d+)\s+in\s+the\s+form\s+(\d+)q\s*\+\s*r", prompt, re.IGNORECASE)
        if division_lemma:
            divisor = int(division_lemma.group(2)) + 2
            quotient = max(2, int(division_lemma.group(1)) // int(division_lemma.group(2)) - 1)
            remainder = 1
            dividend = divisor * quotient + remainder
            generated.update({
                "prompt": f"Using Euclid's division lemma, write {dividend} in the form {divisor}q + r. What are q and r?",
                "answer_type": "pair",
                "answer": [quotient, remainder],
                "answer_labels": ["q", "r"],
                "hint": f"Divide {dividend} by {divisor}.",
                "steps": [
                    f"Divide {dividend} by {divisor}.",
                    f"The quotient is {quotient}.",
                    f"The remainder is {remainder}, so {dividend} = {divisor} x {quotient} + {remainder}.",
                ],
            })
            generated["difficulty"] = "easy"
            generated["source"] = "cbse_mini_check"
            return generated

        numbers = [int(item) for item in re.findall(r"-?\d+", prompt)]
        if numbers:
            replacements = [number + 2 if number >= 0 else number - 2 for number in numbers]
            new_prompt = prompt
            for old, new in zip(numbers, replacements):
                new_prompt = re.sub(rf"(?<!\d){re.escape(str(old))}(?!\d)", str(new), new_prompt, count=1)
            generated["prompt"] = new_prompt if new_prompt != prompt else f"Use the same idea for a new easy case: {prompt}"
            if source.get("answer_type") == "number" and isinstance(source.get("answer"), (int, float)):
                generated["answer"] = source["answer"] + 2
        else:
            generated["prompt"] = f"Explain one easy new example of {concept.get('title', 'this concept')} in your own words."
            generated["answer_type"] = "text"
            generated["answer"] = "explained"
            generated["accepted_answers"] = ["explained", "yes"]

        generated["difficulty"] = "easy"
        generated["source"] = "cbse_mini_check"
        generated["hint"] = generated.get("hint") or "Use the same idea, but do not copy the worked example."
        if generated.get("prompt") == prompt:
            generated["prompt"] = f"Try a different easy question for {concept.get('title', 'this concept')}."
        return generated

    def _build_voice_text(self, explanation: str, steps: list[str] | None = None) -> str:
        parts = ["Let's understand this step by step.", self._sentence(explanation)]
        clean_steps = [self._sentence(step) for step in (steps or []) if self._sentence(step)]
        if clean_steps:
            parts.append("First, " + clean_steps[0].lstrip("Step 1: ").strip())
            for step in clean_steps[1:4]:
                parts.append("Then, " + re.sub(r"^Step\s*\d+\s*:\s*", "", step).strip())
        return self._sentence(" ".join(parts))

    def _next_adaptive_problem(self, state: ClassroomState) -> dict[str, Any]:
        state.last_questions = getattr(state, "last_questions", [])
        current_prompt = (getattr(state, "active_problem", None) or {}).get("prompt")
        blocked_prompts = set(state.last_questions)
        if current_prompt:
            blocked_prompts.add(current_prompt)

        next_problem = self._generate_adaptive_problem(state)

        for _ in range(5):
            prompt = next_problem.get("prompt")
            if prompt and prompt not in blocked_prompts:
                break
            next_problem = self._generate_adaptive_problem(state)

        prompt = next_problem.get("prompt")
        if prompt:
            state.last_questions.append(prompt)
            state.last_questions = state.last_questions[-5:]

        state.active_problem = next_problem
        return next_problem

    def _format_next_question(self, exam: str, next_problem: dict[str, Any]) -> str:
        prompt = next_problem.get("prompt", "")
        if _normalize_exam(exam) == "jee":
            return f"Next (JEE level):\n\n{prompt}"
        return f"Try this similar question:\n\n{prompt}"

    def _speed_hint(self, exam: str, mistake_type: str | None = None) -> str | None:
        if _normalize_exam(exam) != "jee":
            return None
        if mistake_type == "missing_root":
            return "For x^2 = a, write both roots immediately: x = plus/minus sqrt(a)."
        if mistake_type == "sign_error":
            return "Before expanding, mark root signs and verify the sum/product mentally."
        if mistake_type == "concept_error":
            return "First identify the fastest route: factorization, identity, or quadratic formula."
        return "After solving, substitute once mentally to reject impossible roots."

    def _classify_jee_pattern(self, prompt: str) -> str:
        cleaned = clean_expression(prompt)
        if re.fullmatch(r"x\*\*2[+-]\d+", cleaned):
            return "quadratic_difference_of_squares"
        if "x**2" in cleaned and re.search(r"[+-]\d+\*x", cleaned):
            return "quadratic_factor_pair"
        return "quadratic_formula"

    def _update_jee_performance(self, state: ClassroomState, pattern: str, correct: bool) -> None:
        state.pattern_stats = getattr(state, "pattern_stats", {})
        state.pattern_stats.setdefault(pattern, {"correct": 0, "wrong": 0})
        bucket = "correct" if correct else "wrong"
        state.pattern_stats[pattern][bucket] += 1

        state.correct_streak = getattr(state, "correct_streak", 0)
        state.wrong_streak = getattr(state, "wrong_streak", 0)
        if correct:
            state.correct_streak += 1
            state.wrong_streak = 0
        else:
            state.wrong_streak += 1
            state.correct_streak = 0

        levels = ["easy", "medium", "hard"]
        current = getattr(state, "difficulty", "easy")
        index = levels.index(current) if current in levels else 0
        if state.correct_streak >= 3:
            state.difficulty = levels[min(index + 1, len(levels) - 1)]
            state.correct_streak = 0
        elif state.wrong_streak >= 2:
            state.difficulty = levels[max(index - 1, 0)]
            state.wrong_streak = 0

    def _weakest_jee_pattern(self, state: ClassroomState) -> str:
        pattern_stats = getattr(state, "pattern_stats", {})
        if not pattern_stats:
            return "quadratic_difference_of_squares"
        return min(
            pattern_stats,
            key=lambda p: pattern_stats[p]["correct"] / max(1, pattern_stats[p]["correct"] + pattern_stats[p]["wrong"]),
        )

    def _next_jee_question(self, state: ClassroomState) -> dict[str, Any]:
        state.last_questions = getattr(state, "last_questions", [])
        current_prompt = (getattr(state, "active_problem", None) or {}).get("prompt")
        blocked_prompts = set(state.last_questions)
        if current_prompt:
            blocked_prompts.add(current_prompt)

        pattern = self._weakest_jee_pattern(state)
        difficulty = getattr(state, "difficulty", "easy")
        question = self._generate_jee_question(pattern, difficulty)
        for _ in range(8):
            if question["prompt"] not in blocked_prompts:
                break
            question = self._generate_jee_question(pattern, difficulty)

        state.last_questions.append(question["prompt"])
        state.last_questions = state.last_questions[-5:]
        state.active_problem = question
        return question

    def _generate_jee_question(self, pattern: str, difficulty: str) -> dict[str, Any]:
        if pattern == "quadratic_difference_of_squares":
            ranges = {"easy": (2, 8), "medium": (6, 15), "hard": (10, 25)}
            lo, hi = ranges.get(difficulty, ranges["easy"])
            a = random.randint(lo, hi)
            prompt = f"x^2 - {a * a} = 0"
        elif pattern == "quadratic_factor_pair":
            ranges = {"easy": (1, 5), "medium": (2, 9), "hard": (4, 14)}
            lo, hi = ranges.get(difficulty, ranges["easy"])
            r1 = random.randint(lo, hi)
            r2 = -random.randint(lo, hi) if difficulty != "easy" else random.randint(lo, hi)
            b = -(r1 + r2)
            c = r1 * r2
            prompt = f"x^2 {b:+}x {c:+} = 0"
        else:
            ranges = {"easy": (1, 4), "medium": (2, 7), "hard": (3, 10)}
            lo, hi = ranges.get(difficulty, ranges["easy"])
            a = random.randint(2, 4 if difficulty == "easy" else 6)
            r1 = random.randint(lo, hi)
            r2 = random.randint(lo, hi)
            b = -a * (r1 + r2)
            c = a * r1 * r2
            prompt = f"{a}x^2 {b:+}x {c:+} = 0"

        return {
            "prompt": prompt,
            "topic": "quadratic",
            "pattern": pattern,
            "difficulty": difficulty,
            "answer_type": "pair",
        }

    def _build_jee_response(self, question: dict[str, Any], mistake_type: str) -> dict[str, Any]:
        pattern = question.get("pattern") or self._classify_jee_pattern(question.get("prompt", ""))
        if mistake_type == "missing_root":
            explanation = "You found only one root. A quadratic can have two roots."
            steps = ["Move to standard form.", "Solve for both possible roots.", "Check both values in the equation."]
            shortcut = "For x^2 = a, answer is plus/minus sqrt(a)."
            speed_hint = "Write both signs immediately before simplifying."
        elif mistake_type == "sign_error":
            explanation = "The root signs do not match the equation."
            steps = ["Compare root sum and product.", "Fix the sign using -b/a.", "Verify by substitution."]
            shortcut = "Use sum of roots = -b/a and product = c/a."
            speed_hint = "Check signs from sum/product before doing long steps."
        else:
            explanation = "The solving method is off for this pattern."
            steps = ["Identify the quadratic pattern.", "Choose factorization or formula.", "Verify roots quickly."]
            shortcut = "If factorization is not visible in 5 seconds, use the quadratic formula."
            speed_hint = "Pattern first, calculation second."

        if pattern == "quadratic_formula":
            shortcut = "Use discriminant first: D = b^2 - 4ac."

        return {
            "mistake_explanation": explanation,
            "concept_steps": steps[:3],
            "shortcut": shortcut,
            "speed_hint": speed_hint,
        }

    def _concept_check_question(self, concept: dict[str, Any]) -> dict[str, Any]:
        for key in ("practice_problems", "exercise_problems", "ncert_examples"):
            problems = concept.get(key) or []
            if problems:
                return dict(problems[0])
        return self._generate_jee_question("quadratic_difference_of_squares", "easy")

    def _concept_board_problems(self, state: ClassroomState, concept: dict[str, Any]) -> list[dict[str, Any]]:
        if _normalize_exam(getattr(state, "exam", "cbse")) == "jee":
            return []
        textbook_examples = [dict(problem, source="ncert_example") for problem in concept.get("ncert_examples", []) if isinstance(problem, dict)]
        exercise_types = [dict(problem, source="textbook_exercise") for problem in concept.get("exercise_problems", []) if isinstance(problem, dict)]
        if not textbook_examples:
            textbook_examples = [dict(problem, source="practice_example") for problem in concept.get("practice_problems", []) if isinstance(problem, dict)]
        return [*textbook_examples, *exercise_types]

    def _homework_exercise_questions(self, concept: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            dict(problem, source="textbook_exercise", can_request_help=True)
            for problem in concept.get("exercise_problems", [])
            if isinstance(problem, dict)
        ]

    def _concept_example(self, concept: dict[str, Any]) -> str | None:
        examples = concept.get("ncert_examples") or concept.get("practice_problems") or []
        if examples:
            return examples[0].get("prompt")
        board_work = concept.get("board_work") or []
        return board_work[0] if board_work else None

    def generate_homework(self, state: ClassroomState, topic=None) -> list[dict[str, Any]]:
        if not self._is_practice_phase(state):
            return []

        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        if exam == "jee":
            patterns = ["quadratic_difference_of_squares", "quadratic_factor_pair", "quadratic_formula"]
            return [self._generate_jee_question(pattern, getattr(state, "difficulty", "easy")) for pattern in patterns]

        topic_obj = find_topic_by_message(state.grade, str(topic or "")) or get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concepts = get_topic_concepts(state.grade, topic_obj["slug"]) if topic_obj else []
        questions: list[dict[str, Any]] = []
        for concept in concepts:
            exercise_questions = self._homework_exercise_questions(concept)
            for question in exercise_questions:
                question["topic"] = topic_obj.get("title", "CBSE Mathematics") if topic_obj else "CBSE Mathematics"
                question["concept"] = concept.get("title")
                questions.append(question)
                if len(questions) >= 5:
                    break
            if len(questions) >= 5:
                break
        return questions or [self._generate_jee_question("quadratic_difference_of_squares", "easy")]

    def _evaluate_homework_answer(self, question: dict[str, Any], answer: str) -> dict[str, Any]:
        try:
            expected = question.get("answer")
            if expected is not None:
                accepted = expected if isinstance(expected, list) else [expected]
                parsed = parse_input(answer)
                if parsed is not None:
                    correct = _answers_match(parsed, sorted(float(x) for x in accepted))
                else:
                    correct = str(answer).strip().lower() in {str(x).strip().lower() for x in accepted}
                return {"correct": correct, "mistake_type": None if correct else "concept_error"}

            expr = clean_expression(question.get("prompt", ""))
            x = symbols("x")
            expected_roots = sorted(float(s.evalf()) for s in solve(expr, x) if s.is_real)
            parsed_roots = parse_input(answer) or []
            correct = _answers_match(parsed_roots, expected_roots)
            if correct:
                mistake_type = None
            elif len(parsed_roots) < len(expected_roots):
                mistake_type = "missing_root"
            else:
                mistake_type = "concept_error"
            return {"correct": correct, "mistake_type": mistake_type}
        except Exception:
            return {"correct": False, "mistake_type": "concept_error"}

    def handle_exam(self, state, payload):
        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        data = payload if isinstance(payload, dict) else {}
        action = data.get("action", "next")

        if action == "start" or not getattr(state, "exam_state", None):
            patterns = ["quadratic_difference_of_squares", "quadratic_factor_pair", "quadratic_formula"]
            questions = [
                self._generate_jee_question(patterns[index % len(patterns)], ["easy", "medium", "hard"][min(index // 3, 2)])
                for index in range(9)
            ]
            state.exam_state = {"questions": questions, "timer": 30 * 60, "score": 0, "current_index": 0, "answers": []}

        exam_state = state.exam_state

        if action == "submit":
            answer = str(data.get("answer", ""))
            index = exam_state.get("current_index", 0)
            question = exam_state["questions"][index]
            result = self._evaluate_homework_answer(question, answer)
            delta = 4 if result["correct"] else (-1 if exam == "jee" and answer else 0)
            exam_state["score"] += delta
            exam_state["answers"].append({"answer": answer, **result})
            exam_state["current_index"] = min(index + 1, len(exam_state["questions"]) - 1)

        index = exam_state.get("current_index", 0)
        question = exam_state["questions"][index]
        return {
            "question": question.get("prompt"),
            "time_left": exam_state.get("timer", 0),
            "question_number": index + 1,
            "score": exam_state.get("score", 0),
        }

    def get_notes(self, topic):
        title = str(topic or "Quadratic Equations")
        return {
            "formulas": ["ax^2 + bx + c = 0", "D = b^2 - 4ac", "x = (-b +/- sqrt(D)) / 2a"],
            "key_points": [f"Identify the pattern in {title}.", "Check both roots.", "Verify by substitution."],
            "common_mistakes": ["Missing one root", "Wrong sign", "Using formula before simplifying"],
        }
    

    def _generate_adaptive_problem(self, state):
        level = getattr(state, "level", None) or self.get_difficulty(state)
        weak = state.get_weak_area()

        def make_roots_problem(r1, r2):
            # build quadratic from roots
            # (x - r1)(x - r2) = x^2 - (r1+r2)x + r1*r2
            b = -(r1 + r2)
            c = r1 * r2
            return f"x^2 {b:+}x {c:+} = 0"

        # -------------------------
        # 🎯 Weakness targeting
        # -------------------------
        if weak == "missing_root":
            a = random.randint(2, 10)
            return {
                "prompt": f"x^2 - {a*a} = 0",
                "answer_type": "pair"
            }

        if weak == "sign_error":
            r1 = random.randint(1, 5)
            r2 = -random.randint(1, 5)
            return {
                "prompt": make_roots_problem(r1, r2),
                "answer_type": "pair"
            }

        # -------------------------
        # 🎯 Difficulty control
        # -------------------------
        if level == "easy":
            a = random.randint(2, 6)
            return {
                "prompt": f"x^2 - {a*a} = 0",
                "answer_type": "pair"
            }

        elif level == "medium":
            r1 = random.randint(1, 5)
            r2 = random.randint(1, 5)
            return {
                "prompt": make_roots_problem(r1, r2),
                "answer_type": "pair"
            }

        else:  # hard
            a = random.randint(1, 3)
            b = random.randint(-7, 7)
            c = random.randint(-6, 6)

            return {
                "prompt": f"{a}x^2 {b:+}x {c:+} = 0",
                "answer_type": "pair"
            }

    def _refresh_public_state(self, state: ClassroomState, include_problem: bool) -> None:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        state.public_state["topic_name"] = (
            getattr(state, "current_concept_title", None)
            or state.topic_title
            or "Introduction"
        )
        state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
        state.class_duration_minutes = CLASS_DURATION_MINUTES
        state.topic_title = topic["title"] if topic else state.topic_title
        state.concept_title = concept["title"] if concept else state.concept_title
        state.homework = self._build_homework(topic, concept)
        state.note_cards = self._build_note_cards(topic, concept)
        state.whiteboard = self._build_whiteboard(topic, concept, state.active_problem if include_problem else None)
        topic_title = topic["title"] if topic else "Math lesson"
        if concept and include_problem and state.active_problem:
            state.summary = (
                f"{state.chapter_label}: {topic_title} - teaching {concept['title']} "
                "and waiting for the student's answer."
            )
        elif concept:
            state.summary = (
                f"{state.chapter_label}: {topic_title} - focused on {concept['title']} "
                f"in a {CLASS_DURATION_MINUTES}-minute lesson."
            )
        else:
            state.summary = f"{state.chapter_label}: {topic_title} - lesson is ready."

    def _build_note_cards(self, topic: dict | None, concept: dict | None) -> list[str]:
        cards: list[str] = [f"Class format: {CLASS_DURATION_MINUTES} minutes - concept, board work, practice, homework."]
        if topic:
            cards.extend([topic.get("teaching_anchor", ""), topic.get("classroom_goal", ""), topic.get("summary", "")])
        if concept:
            cards.append(concept.get("explanation", ""))
            cards.extend(concept.get("board_work", [])[:2])
        return [card for card in dict.fromkeys(card.strip() for card in cards if card and card.strip())][:6]

    def _build_whiteboard(self, topic: dict | None, concept: dict | None, problem: dict[str, Any] | None) -> dict[str, Any]:
        board_work = concept.get("board_work", []) if concept else []
        equations = [line for line in board_work if "=" in line]
        if topic and topic.get("teaching_anchor") and "=" in topic["teaching_anchor"]:
            equations = [topic["teaching_anchor"], *equations]
        equations = [line for line in dict.fromkeys(line.strip() for line in equations if line and line.strip())][:5]

        chalk_lines: list[str] = []
        if concept and concept.get("title"):
            chalk_lines.append(f"Focus: {concept['title']}")
        if concept and concept.get("definition"):
            chalk_lines.append(concept["definition"])
        elif topic and topic.get("teaching_anchor") and "=" not in topic["teaching_anchor"]:
            chalk_lines.append(topic["teaching_anchor"])
        chalk_lines.extend(line for line in board_work if "=" not in line)
        chalk_lines = [line for line in dict.fromkeys(line.strip() for line in chalk_lines if line and line.strip())][:6]
        whiteboard = {
            "title": topic["title"] if topic else "CBSE Mathematics",
            "subtitle": concept["title"] if concept else "Guided board",
            "chalk_lines": chalk_lines,
            "equations": equations,
        }
        if concept and isinstance(concept.get("graph"), dict):
            whiteboard["graph"] = concept["graph"]
        elif problem and isinstance(problem.get("graph"), dict):
            whiteboard["graph"] = problem["graph"]
        if problem:
            whiteboard["problem"] = problem["prompt"]
        return whiteboard

    def _remember_session_notes(
        self,
        state: ClassroomState,
        topic: dict[str, Any] | None,
        concept: dict[str, Any] | None,
        extra_notes: list[str] | None = None,
    ) -> list[str]:
        notes = list(getattr(state, "session_notes", []) or [])
        if topic and topic.get("title"):
            notes.append(f"Chapter covered: {topic['title']}")
        if concept and concept.get("title"):
            notes.append(f"Concept covered: {concept['title']}")
        important = self._important_memory_note(topic, concept)
        if important:
            notes.append(important)
        if extra_notes:
            notes.extend(extra_notes)

        state.session_notes = [
            note for note in dict.fromkeys(str(item).strip() for item in notes if str(item).strip())
        ][:20]
        state.note_cards = [
            note for note in dict.fromkeys([*getattr(state, "note_cards", []), *state.session_notes])
        ][:8]
        return state.session_notes

    def _slow_voice_text(
        self,
        state: ClassroomState,
        concept: dict[str, Any] | None,
        explanation: str,
        extra: str | None = None,
    ) -> str:
        parts = [
            f"{state.chapter_label}.",
            f"Topic: {state.topic_title}.",
        ]
        if concept and concept.get("title"):
            parts.append(f"Concept: {concept['title']}.")
        parts.extend([
            "We will go slowly.",
            explanation,
        ])
        if extra:
            parts.append(extra)
        parts.append("Pause. Look at the whiteboard before we continue.")
        return " ".join(part for part in parts if part)

    def _prepare_concept_board(
        self,
        state: ClassroomState,
        topic: dict[str, Any] | None,
        concept: dict[str, Any] | None,
        problem: dict[str, Any] | None = None,
        *,
        mode: str = "concept",
    ) -> dict[str, Any]:
        state.whiteboard = self._build_whiteboard(topic, concept, problem)
        state.whiteboard["mode"] = mode
        if problem:
            state.whiteboard["problem"] = problem.get("prompt")
            state.whiteboard["solution_steps"] = [
                str(step).strip() for step in problem.get("steps", []) if str(step).strip()
            ][:5]
            if problem.get("answer") is not None:
                state.whiteboard["answer"] = self._format_expected_answer(problem)
        return state.whiteboard

    def _class_homework_response(
        self,
        state: ClassroomState,
        chapter: dict[str, Any] | None = None,
        topic: dict[str, Any] | None = None,
        concept: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._is_practice_phase(state):
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=chapter,
                topic=topic,
                concept=concept,
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )

        topic_obj = topic or get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        questions = self.generate_homework(state, topic_obj.get("title") if topic_obj else state.topic_title)
        if not questions:
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=chapter or topic_obj,
                topic=topic_obj,
                concept=concept,
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )
        state.homework_questions = questions
        state.homework = [
            question.get("prompt", str(question)) if isinstance(question, dict) else str(question)
            for question in questions
        ][:5]
        state.homework_chapter_index = getattr(state, "current_chapter_index", 0)
        state.homework_topic_index = getattr(state, "current_topic_index", 0)
        state.homework_concept_index = getattr(state, "current_concept_index", 0)
        notes = self._remember_session_notes(state, topic_obj, concept, ["Homework assigned for revision."])
        return self._class_response(
            response_type="homework",
            state=state,
            chapter=chapter or topic_obj,
            topic=topic_obj,
            concept=concept,
            explanation="Class is complete for today. Homework is ready, and I saved the important notes from this session.",
            steps=[],
            next_action="homework",
            voice_text="Good work today. I have saved your important notes and prepared homework for revision.",
            homework=questions,
            session_notes=notes,
        )

    def _advance_after_homework(self, state: ClassroomState) -> dict[str, Any]:
        state.homework = []
        state.homework_questions = []
        if getattr(state, "homework_chapter_index", None) is not None:
            state.current_chapter_index = int(state.homework_chapter_index)
        if getattr(state, "homework_topic_index", None) is not None:
            state.current_topic_index = int(state.homework_topic_index)
        if getattr(state, "homework_concept_index", None) is not None:
            state.current_concept_index = int(state.homework_concept_index)
        state.homework_chapter_index = None
        state.homework_topic_index = None
        state.homework_concept_index = None
        state.class_last_step = "evaluation"

        next_result = self._next_concept(state)
        if next_result.get("type") == "chapter_complete":
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="chapter_complete",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation="Homework skipped for now. The chapter flow is complete.",
                steps=[],
                next_action="test",
                voice_text="Homework skipped for now. The chapter flow is complete.",
            )

        return self._teach_concept(state)

    def _skip_homework_response(self, state: ClassroomState) -> dict[str, Any]:
        return self._advance_after_homework(state)

    def _get_cbse_context(self, query: str, session: ClassroomState) -> str:
        try:
            user_input = self._sentence(query)
            raw_phase = getattr(session, "active_phase", SessionPhase.TEACHING)
            phase_value = str(getattr(raw_phase, "value", raw_phase) or SessionPhase.TEACHING.value).strip().lower()
            exam_type = _normalize_exam(getattr(session, "exam", "cbse"))
            grade = int(getattr(session, "grade", 10) or 10)
            return retrieve_context(
                query=user_input,
                chapter=session.current_chapter,
                phase=phase_value,
                exam_type=exam_type,
                grade=grade,
                k=8,
            )
        except Exception as error:
            print("Retrieval error:", error)
            return ""

    def _supporting_ncert_point(self, query: str, session: ClassroomState) -> str:
        context = self._get_cbse_context(query, session)
        if not context:
            return ""
        flat = " ".join(context.split())
        flat = re.sub(r"Reprint\s+\d{4}-\d{2}", "", flat, flags=re.IGNORECASE)
        flat = re.sub(r"\b[A-Z][A-Z\s]{8,}\s+\d+\b", "", flat)
        flat = re.sub(r"\s+", " ", flat).strip()
        sentences = re.split(r"(?<=[.!?])\s+", flat)
        for sentence in sentences:
            cleaned = sentence.strip()
            if 40 <= len(cleaned) <= 180:
                return cleaned
        return flat[:160].strip()

    def _is_doubt_followup(self, question: str) -> bool:
        lowered = self._sentence(question).lower()
        if not lowered:
            return False
        followup_phrases = (
            "explain in detail",
            "give example",
            "giving example",
            "another example",
            "more detail",
            "i did not understand",
            "didn't understand",
            "not clear",
            "explain again",
            "can you explain",
        )
        return any(phrase in lowered for phrase in followup_phrases)

    def _integers_from_text(self, text: str) -> list[int]:
        return [int(match) for match in re.findall(r"\b\d+\b", str(text or ""))]

    def _divisor_requested_after_by(self, text: str) -> int | None:
        match = re.search(r"\bby\s+(\d+)\b", str(text or "").lower())
        if not match:
            return None
        divisor = int(match.group(1))
        return divisor if divisor > 1 else None

    def _smallest_divisor(self, number: int) -> int | None:
        if number < 2:
            return None
        if number % 2 == 0:
            return 2
        candidate = 3
        while candidate * candidate <= number:
            if number % candidate == 0:
                return candidate
            candidate += 2
        return None

    def _looks_like_factor_search(self, lowered: str) -> bool:
        cues = (
            "by 2 then 3",
            "then 3 and so on",
            "one by one",
            "first divisor",
            "first diviser",
            "smallest divisor",
            "smallest factor",
            "which number divides",
            "what divides",
            "by which number",
            "which number i can divide",
            "which number can i divide",
            "can divide given number",
            "given number can divide",
            "divide given number",
            "divide the given number",
            "without trying",
        )
        return any(cue in lowered for cue in cues) or (
            "given" in lowered and (
                "divisor" in lowered
                or "diviser" in lowered
                or "factor" in lowered
                or "divide" in lowered
                or "divisible number" in lowered
            )
        )

    def _looks_like_next_multiple_search(self, lowered: str, requested_divisor: int | None) -> bool:
        if requested_divisor is None:
            return False
        cues = (
            "starting from",
            "start from",
            "after",
            "at or after",
            "next multiple",
            "next divisible",
            "first number divisible by",
            "first number at",
            "jump to",
            "jump on",
        )
        return any(cue in lowered for cue in cues)

    def _looks_like_divisibility_rule_question(self, lowered: str) -> bool:
        return "divisibility rule" in lowered or "divisibility rules" in lowered

    def _build_divisibility_rules_response(self, number: int | None = None) -> dict[str, Any]:
        steps = [
            "Divisible by 2: the last digit is even.",
            "Divisible by 3: the sum of digits is divisible by 3.",
            "Divisible by 5: the last digit is 0 or 5.",
            "Divisible by 9: the sum of digits is divisible by 9.",
            "Divisible by 10: the last digit is 0.",
            "For 7, 11, 13 and bigger primes, use a specific test or normal division only after the quick rules fail.",
        ]
        explanation = (
            "A divisibility rule is a shortcut to check whether a number can be divided exactly by another number "
            "without doing full long division. It helps you quickly find possible divisors."
        )
        if number is not None:
            digit_sum = sum(int(digit) for digit in str(abs(number)))
            checks = []
            checks.append(
                f"{number} is {'divisible' if number % 2 == 0 else 'not divisible'} by 2 because its last digit is "
                f"{str(abs(number))[-1]}."
            )
            checks.append(
                f"The digit sum is {digit_sum}, so {number} is "
                f"{'divisible' if number % 3 == 0 else 'not divisible'} by 3."
            )
            checks.append(
                f"{number} is {'divisible' if str(abs(number))[-1] in {'0', '5'} else 'not divisible'} by 5."
            )
            explanation = f"{explanation} For your number {number}: " + " ".join(checks)

        return {
            "mistake_explanation": explanation,
            "concept_steps": steps,
            "shortcut": "For a big number, check 2, 3, 5, 9, and 10 mentally first.",
            "speed_hint": "Digit-sum rules for 3 and 9 are often the fastest for large numbers.",
        }

    def _build_factor_search_response(self, number: int | None) -> dict[str, Any]:
        steps = [
            "Check divisibility by 2 first: the last digit must be even.",
            "Then check divisibility by 3: add the digits; if the sum is divisible by 3, the number is divisible by 3.",
            "Then check 5: the last digit must be 0 or 5.",
            "After that, check prime numbers only: 7, 11, 13, 17, and so on.",
            "Stop when the prime you are testing becomes bigger than the square root of the number.",
        ]
        if number is None:
            return {
                "mistake_explanation": (
                    "To find the first divisor of a big number, do not try every number. "
                    "Use divisibility rules in order: 2, then 3, then 5, then prime divisors like 7, 11, 13. "
                    "The first one that divides exactly is the smallest divisor greater than 1."
                ),
                "concept_steps": steps,
                "shortcut": "Check 2, 3, and 5 mentally before doing long division.",
                "speed_hint": "For divisor search, test only primes after 5.",
            }

        digit_sum = sum(int(digit) for digit in str(abs(number)))
        divisor = self._smallest_divisor(abs(number))
        if divisor is None:
            result = (
                f"For {number}, no divisor greater than 1 is found up to the square root, "
                "so it is prime."
            )
        elif divisor == 2:
            result = f"For {number}, the last digit is even, so the first divisor greater than 1 is 2."
        elif divisor == 3:
            result = (
                f"For {number}, the digit sum is {digit_sum}. "
                f"Because {digit_sum} is divisible by 3, {number} is divisible by 3. "
                f"So the first divisor greater than 1 is 3, and {number} = 3 x {abs(number) // 3}."
            )
        elif divisor == 5:
            result = f"For {number}, the last digit is 0 or 5, so the first divisor greater than 1 is 5."
        else:
            result = (
                f"For {number}, 2, 3, and 5 do not divide it. "
                f"The first divisor greater than 1 is {divisor}, and {number} = {divisor} x {abs(number) // divisor}."
            )

        return {
            "mistake_explanation": (
                "You are asking how to quickly find the first divisor of a big number. "
                "There is no single visual trick for every number, but there is a fast order of checks. "
                f"{result}"
            ),
            "concept_steps": steps,
            "shortcut": "Use divisibility rules first; only use division when the quick tests fail.",
            "speed_hint": "Do not test 4, 6, 8, 9 after primes blindly; if 2 or 3 already fails, many composites are unnecessary.",
        }

    def _build_next_multiple_response(self, start_number: int | None, divisor: int | None) -> dict[str, Any]:
        steps = [
            "Call the starting number N and the divisor d.",
            "Divide N by d and find the remainder r.",
            "If r = 0, then N is already divisible by d.",
            "If r is not 0, add d - r to N.",
            "Formula: first number at or after N divisible by d = N + ((d - N % d) % d).",
        ]
        if start_number is None or divisor is None:
            return {
                "mistake_explanation": (
                    "To jump directly to the next divisible number, I need two values: "
                    "the starting number N and the divisor d. Then divide N by d once, find the remainder, "
                    "and add the missing amount d - remainder."
                ),
                "concept_steps": steps,
                "shortcut": "Next divisible number = N + ((d - N % d) % d).",
                "speed_hint": "One remainder calculation replaces checking numbers one by one.",
            }

        remainder = start_number % divisor
        add_amount = (divisor - remainder) % divisor
        answer = start_number + add_amount
        if add_amount == 0:
            result = f"{start_number} is already divisible by {divisor}, so the answer is {start_number}."
        else:
            result = (
                f"{start_number} divided by {divisor} leaves remainder {remainder}. "
                f"Add {divisor} - {remainder} = {add_amount}. "
                f"So the first number at or after {start_number} divisible by {divisor} is {answer}."
            )
        return {
            "mistake_explanation": (
                "This is a next-multiple problem. You do not need to try each number one by one. "
                f"{result}"
            ),
            "concept_steps": steps,
            "shortcut": "Next divisible number = N + ((d - N % d) % d).",
            "speed_hint": "Use the remainder to jump directly to the answer.",
        }

    def _parse_ai_doubt_plan(self, text: str) -> dict[str, Any] | None:
        raw = str(text or "").strip()
        if not raw:
            return None
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None
        try:
            payload = json.loads(match.group())
        except Exception:
            return None
        explanation = self._sentence(payload.get("explanation") or payload.get("mistake_explanation"))
        raw_steps = payload.get("steps") or payload.get("concept_steps") or []
        steps = [self._sentence(step) for step in raw_steps if self._sentence(step)]
        if not explanation:
            return None
        return {
            "mistake_explanation": explanation or "Unable to generate response. Please try rephrasing your question.",
            "concept_steps": steps[:8] if steps else [],
            "shortcut": self._sentence(payload.get("shortcut")) or None,
            "speed_hint": self._sentence(payload.get("speed_hint")) or None,
        }

    def _ai_doubt_context(self, state: ClassroomState, question: str) -> str:
        topic = getattr(state, "topic_title", None) or getattr(state, "current_topic", None) or "Current mathematics topic"
        concept = (
            getattr(state, "concept_title", None)
            or getattr(state, "current_concept", None)
            or getattr(state, "current_concept_title", None)
            or topic
        )
        active_problem = getattr(state, "active_problem", None)
        problem_text = ""
        if isinstance(active_problem, dict):
            problem_text = str(active_problem.get("prompt") or active_problem.get("question") or "").strip()
        whiteboard = getattr(state, "whiteboard", None)
        board_lines: list[str] = []
        if isinstance(whiteboard, dict):
            if not problem_text:
                problem_text = str(whiteboard.get("problem") or "").strip()
            raw_lines = whiteboard.get("chalk_lines") or whiteboard.get("solution_steps") or []
            if isinstance(raw_lines, list):
                board_lines = [self._sentence(line) for line in raw_lines if self._sentence(line)][:12]
        return (
            f"Grade: {getattr(state, 'grade', 10)}\n"
            f"Exam: {getattr(state, 'exam', 'cbse')}\n"
            f"Chapter/topic: {topic}\n"
            f"Current concept: {concept}\n"
            f"Current board problem: {problem_text or 'None'}\n"
            f"Current blackboard lines: {' | '.join(board_lines) if board_lines else 'None'}\n"
            f"Previous doubt: {getattr(state, 'last_doubt_question', None) or 'None'}\n"
            f"Student question: {question}"
        )

    def _build_ai_doubt_response(self, state: ClassroomState, question: str) -> dict[str, Any] | None:
        from app.services.ai_gateway import generate_response

        topic = getattr(state, "topic_title", None) or getattr(state, "current_topic", None) or "Current mathematics topic"
        active_problem = getattr(state, "active_problem", None) or {}
        problem_text = str(active_problem.get("prompt") or active_problem.get("question") or "").strip()
        
        prompt = f"""
You are Arvind Sir, an expert Class 10-12 mathematics tutor.

CURRENT CLASS CONTEXT:
- Chapter/Topic: {topic}
- Current Problem: {problem_text or 'None'}

STUDENT QUESTION: {question}

INSTRUCTIONS (FOLLOW STRICTLY):
1. ANSWER DIRECTLY AND SPECIFICALLY about the current problem/topic. Do NOT give generic study advice.
2. If student's question relates to the current problem, explain the concept using THAT problem as an example.
3. If prerequisite concepts are missing, FIRST explain those concepts slowly and clearly with examples, THEN connect to current problem.
4. ALWAYS structure your answer as:
   - What the student asked (clarification)
   - The prerequisite concept (if any, explained step-by-step)
   - The specific answer with numbers/formulas
   - Why this matters for the current problem
5. For any calculation, show the actual numbers and steps. Do NOT give formula-only answers.
6. Use Hindi/Hinglish for explanation but keep mathematics terms in English.
7. Keep sentences short and simple for an Indian school student.
8. Return ONLY valid JSON, no markdown, no code blocks.

Context from blackboard: {self._ai_doubt_context(state, question)}

Return ONLY JSON:
{{
  "explanation": "detailed answer with prerequisite concepts explained step-by-step if needed, then the specific answer (6-10 sentences)",
  "steps": ["step 1 with actual numbers", "step 2", "step 3"],
  "shortcut": "optional shortcut if available",
  "speed_hint": "optional exam time-saving hint"
}}
""".strip()

        session_id = getattr(state, 'session_id', None) or getattr(state, 'session', None) or 'anon'
        cache_key = f"ai_doubt|{session_id}|{getattr(state, 'grade', 10)}|{getattr(state, 'exam', 'cbse')}|{question[:500]}"
        cached = get_cache(cache_key)
        if isinstance(cached, dict):
            return cached

        future = AI_DOUBT_EXECUTOR.submit(generate_response, prompt)
        try:
            text = future.result(timeout=15)
        except FutureTimeoutError:
            print(f"[DOUBT] AI generation timed out for question: {question[:100]}")
            return None
        except Exception as error:
            print(f"[DOUBT] AI generation failed: {type(error).__name__}: {error}")
            return None

        plan = self._parse_ai_doubt_plan(text)
        if plan:
            set_cache(cache_key, plan)
        else:
            print(f"[DOUBT] Failed to parse AI response for question: {question[:100]}")
        return plan

    def _build_cbse_doubt_response(self, question: str, state: ClassroomState | None = None, context: str = "") -> dict[str, Any]:
        question_text = self._sentence(question)
        lowered = question_text.lower()
        if state is not None:
            ai_plan = self._build_ai_doubt_response(state, question_text)
            if ai_plan:
                return ai_plan

        numbers = self._integers_from_text(question_text)
        requested_divisor = self._divisor_requested_after_by(question_text)
        if self._looks_like_divisibility_rule_question(lowered):
            number = max(numbers) if numbers else None
            return self._build_divisibility_rules_response(number)

        if self._looks_like_factor_search(lowered):
            number = max(numbers) if numbers else None
            return self._build_factor_search_response(number)

        if self._looks_like_next_multiple_search(lowered, requested_divisor):
            start_candidates = [number for number in numbers if number != requested_divisor]
            start_number = max(start_candidates) if start_candidates else None
            return self._build_next_multiple_response(start_number, requested_divisor)

        if any(token in lowered for token in ("divisible", "diviser", "divisor", "divide", "factor")):
            number = max(numbers) if numbers else None
            return self._build_factor_search_response(number)

        # Use current context to provide a better fallback response
        topic = getattr(state, "topic_title", None) or getattr(state, "current_topic", None) or "this topic"
        problem_text = ""
        active_problem = getattr(state, "active_problem", None)
        if isinstance(active_problem, dict):
            problem_text = str(active_problem.get("prompt") or active_problem.get("question") or "").strip()
        
        # Build a contextual explanation instead of generic one
        explanation = f"Your doubt is: {question_text}\n\n"
        if problem_text:
            explanation += f"Based on the current problem '{problem_text[:80]}...':\n\n"
        explanation += (
            "Let me explain this step-by-step:\n"
            "1. First, identify what information we have (what is given)\n"
            "2. Then, identify what we need to find (what is asked)\n"
            "3. Next, recall the relevant rule, formula, or concept\n"
            "4. Finally, apply it with the actual numbers\n\n"
            "This approach helps you solve similar problems independently."
        )

        return {
            "mistake_explanation": explanation,
            "concept_steps": [
                "Underline the exact quantity asked in the question.",
                "Write the known values separately.",
                "Choose the matching formula, property, or divisibility rule.",
                "Substitute values and simplify one line at a time.",
            ],
            "shortcut": None,
            "speed_hint": None,
        }
    
    def _generate_rag_homework(self, state: ClassroomState, session_id: str, student_id: str):
        """
        Generate homework using CBSE RAG + store in Firebase
        """
        if not self._is_practice_phase(state):
            return {"questions": []}

        topic_name = state.topic_title or "Mathematics"

        context = self._get_cbse_context(topic_name, state)

        questions = []

        if context:
            chunks = context.split("\n\n")[:3]

            for i, chunk in enumerate(chunks):
                questions.append({
                    "question": f"Q{i+1}. {chunk[:120]}",
                    "type": "ncert",
                    "difficulty": "medium"
                })

        # fallback (never empty)
        if not questions:
            questions = [
                {"question": f"Practice problem 1 from {topic_name}"},
                {"question": f"Practice problem 2 from {topic_name}"}
            ]

        homework_payload = {
            "session_id": session_id,
            "student_id": student_id,
            "class": state.grade,
            "chapter": state.chapter_label,
            "topic": topic_name,
            "title": f"{topic_name} Homework",
            "questions": questions
        }

        try:
            save_homework(homework_payload)
        except Exception as e:
            print("Firebase save failed:", e)

        return homework_payload
    
    def get_difficulty(self, state):

        # ✅ SAFE INIT
        state.correct_count = getattr(state, "correct_count", 0)
        state.wrong_count = getattr(state, "wrong_count", 0)
        
        # 🧠 NEW (adaptive stats)
        state.stats = getattr(state, "stats", {
            "total": 0,
            "correct": 0,
            "wrong": 0,
            "by_mistake": {},
            "by_topic": {}
        })

        if state.correct_count >= 3:
            return "medium"
        elif state.wrong_count >= 2:
            return "easy"
        else:
            return "easy"   # start safe
        
    def handle_doubt(self, state, question):
        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        question = self._sentence(question or "")
        effective_question = question
        if self._is_doubt_followup(question) and getattr(state, "last_doubt_question", None):
            effective_question = f"{state.last_doubt_question}. Follow-up request: {question}"

        if exam == "jee":
            pattern = self._classify_jee_pattern(effective_question)
            plan = self._build_jee_response({"prompt": effective_question, "pattern": pattern}, "concept_error")
        else:
            plan = self._build_cbse_doubt_response(effective_question, state=state)

        state.last_doubt_question = effective_question
        state.last_doubt_plan = plan
        
        # Ensure plan has required keys
        if not plan:
            plan = {
                "mistake_explanation": "Unable to process your question right now. Please try again or ask a simpler question.",
                "concept_steps": [],
                "shortcut": None,
                "speed_hint": None,
            }

        return {
            "correct": None,
            "mistake_type": None,
            "hint": plan.get("mistake_explanation", ""),
            "explanation": plan.get("mistake_explanation", ""),
            "steps": plan.get("concept_steps", []),
            "shortcut": plan.get("shortcut") if exam == "jee" else None,
            "speed_hint": plan.get("speed_hint") if exam == "jee" else None,
            "adaptive_hint": None,
            "next_question": None,
        }

    def handle_learn(self, state, topic):
        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        payload = topic if isinstance(topic, dict) else {}
        action = payload.get("action") if isinstance(payload, dict) else None
        topic_text = payload.get("topic") or payload.get("question") if isinstance(payload, dict) else topic
        topic_text = topic_text or state.topic_title or "quadratic equations"
        block_message = self._is_unauthorized_query(state, str(topic_text))
        if block_message:
            return {
                "concept": None,
                "explanation": block_message,
                "example": None,
                "check_question": None,
                "next_action": "continue",
                "topic": state.topic_title,
                "chapter": state.chapter_label,
            }
        topic_obj = find_topic_by_message(state.grade, topic_text) or get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        if topic_obj:
            state.topic_slug = topic_obj["slug"]
            state.topic_title = topic_obj.get("title", topic_obj["slug"])
            state.current_topic = state.topic_slug
            chapter_position, _ = get_chapter_position(state.grade, state.topic_slug)
            state.current_chapter_index = max(chapter_position - 1, 0)

        concepts = get_topic_concepts(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        if action in {"next_topic", "next_chapter"}:
            curriculum = getattr(state, "curriculum", None) or get_grade_curriculum(state.grade)
            chapters = curriculum.get("chapters") or []
            current_index = min(max(getattr(state, "current_chapter_index", 0), 0), max(len(chapters) - 1, 0))
            if current_index + 1 < len(chapters):
                next_chapter = chapters[current_index + 1]
                state.current_chapter_index = current_index + 1
                state.current_topic_index = 0
                state.current_concept_index = 0
                state.topic_slug = next_chapter.get("slug")
                state.topic_title = next_chapter.get("title")
                state.current_topic = state.topic_slug
                state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
                concepts = get_topic_concepts(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
            else:
                return {
                    "concept": None,
                    "explanation": "All topics are complete. You are ready for a test.",
                    "example": None,
                    "check_question": None,
                    "next_action": "test",
                    "topic": state.topic_title,
                    "chapter": state.chapter_label,
                }

        if action in {"next", "next_concept", "continue"} and concepts:
            next_result = self._next_concept(state)
            if next_result.get("type") == "chapter_complete":
                return {
                    "concept": None,
                    "explanation": "This chapter is complete. You are ready for a short test.",
                    "example": None,
                    "check_question": None,
                    "next_action": "test",
                    "topic": state.topic_title,
                    "chapter": state.chapter_label,
                }
            concepts = get_topic_concepts(state.grade, state.topic_slug or get_default_topic_slug(state.grade))

        state.current_concept_index = min(getattr(state, "current_concept_index", 0), max(len(concepts) - 1, 0))
        concept = concepts[state.current_concept_index] if concepts else None
        if not concept:
            return {"concept": None, "explanation": "No concept found.", "example": None, "check_question": None, "next_action": "next_concept"}

        state.concept_id = concept.get("id")
        state.concept_title = concept.get("title", "")
        check_question = self._concept_check_question(concept)
        state.active_problem = check_question

        if exam == "jee":
            pattern = self._classify_jee_pattern(check_question.get("prompt", concept.get("title", "")))
            explanation = concept.get("explanation") or f"Learn the pattern: {pattern.replace('_', ' ')}."
            return {
                "concept": concept.get("title"),
                "explanation": explanation,
                "example": self._concept_example(concept),
                "check_question": check_question.get("prompt"),
                "shortcut": self._build_jee_response({"pattern": pattern, "prompt": check_question.get("prompt", "")}, "concept_error").get("shortcut"),
                "speed_hint": self._speed_hint("jee", None),
                "next_action": "practice" if check_question else "next_concept",
                "topic": state.topic_title,
                "chapter": state.chapter_label,
            }

        context = self._get_cbse_context(concept.get("title", ""), state) or concept.get("explanation", "")
        plan = self._run_lesson_plan(context, exam=exam)
        return {
            "concept": concept.get("title"),
            "explanation": plan.get("mistake_explanation") or concept.get("explanation", ""),
            "example": self._concept_example(concept),
            "check_question": check_question.get("prompt"),
            "steps": plan.get("concept_steps", []),
            "next_action": "practice" if check_question else "next_concept",
            "topic": state.topic_title,
            "chapter": state.chapter_label,
        }

    def _class_topic_from_payload(self, state: ClassroomState, payload: dict[str, Any]) -> None:
        topic_text = payload.get("topic") or payload.get("question") or state.topic_title or "quadratic equations"
        topic_obj = find_topic_by_message(state.grade, str(topic_text)) or get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        if topic_obj:
            state.topic_slug = topic_obj["slug"]
            state.topic_title = topic_obj.get("title", topic_obj["slug"])
            state.current_topic = state.topic_slug
            state.current_chapter = state.topic_title

    def _teacher_agent_payload(self, state: ClassroomState, concept: dict[str, Any]) -> dict[str, Any]:
        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        check_question = self._concept_check_question(concept)
        state.concept_id = concept.get("id")
        state.concept_title = concept.get("title", "")
        state.current_concept = state.concept_title
        state.active_problem = check_question

        if exam == "jee":
            pattern = self._classify_jee_pattern(check_question.get("prompt", concept.get("title", "")))
            plan = self._build_jee_response({"pattern": pattern, "prompt": check_question.get("prompt", "")}, "concept_error")
            explanation = concept.get("explanation") or f"Pattern: {pattern.replace('_', ' ')}."
            steps = plan.get("concept_steps") or [
                f"Recognize {pattern.replace('_', ' ')}.",
                "Use the fastest matching shortcut.",
                "Verify roots mentally.",
            ]
            return {
                "type": "teach",
                "content": {
                    "concept": state.concept_title,
                    "explanation": explanation,
                    "steps": steps[:3],
                    "example": check_question.get("prompt") or self._concept_example(concept),
                    "voice_text": f"{state.concept_title}. {explanation} {plan.get('shortcut') or ''}".strip(),
                    "pattern": pattern.replace("_", " ").title(),
                    "recognition_tip": "Look for a familiar algebraic pattern before expanding.",
                    "shortcut": plan.get("shortcut") or "Use factorization before formula.",
                    "speed_hint": plan.get("speed_hint") or self._speed_hint("jee", None),
                },
            }

        cache_key = f"class|cbse|{concept.get('id')}|{concept.get('title')}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        context = self._get_cbse_context(concept.get("title", ""), state) or concept.get("explanation", "")
        plan = self._run_lesson_plan(context, exam="cbse")
        steps = plan.get("concept_steps") or concept.get("board_work", [])[:3]
        explanation = plan.get("mistake_explanation") or concept.get("explanation", "")
        response = {
            "type": "teach",
            "content": {
                "concept": state.concept_title,
                "explanation": explanation,
                "steps": steps,
                "example": self._concept_example(concept) or check_question.get("prompt"),
                "voice_text": f"{state.concept_title}. {explanation}",
            },
        }
        set_cache(cache_key, response)
        return response

    def _question_agent_payload(self, state: ClassroomState, concept: dict[str, Any]) -> dict[str, Any]:
        question = self._concept_check_question(concept)
        state.active_problem = question
        return {
            "type": "question",
            "content": {
                "explanation": "Mini check.",
                "steps": [],
                "example": question.get("prompt"),
                "voice_text": "Now try this mini check before we continue.",
                "question": question.get("prompt"),
                "concept": concept.get("title"),
            },
        }

    def handle_class(self, state, payload):
        data = payload if isinstance(payload, dict) else {}
        action = data.get("action", "start")
        self._class_topic_from_payload(state, data)

        if action == "start":
            self._set_active_phase(state, SessionPhase.TEACHING)
            state.current_concept_index = 0
            state.class_phase = "teach"
            state.learning_path = [{
                "chapter": self._chapter_label(state.grade, state.topic_slug),
                "topic": state.topic_title,
                "concept_index": 0,
            }]
            return self._theory_welcome_response(state)
        elif action == "repeat":
            state.class_phase = "teach"
        elif action == "next":
            state.class_phase = "question" if getattr(state, "class_phase", "teach") == "teach" else "advance"

        step = self.planner.get_next_step(state)
        concept = step.get("concept")

        if step["type"] == "teach" and concept:
            return self._teacher_agent_payload(state, concept)
        if step["type"] == "question" and concept:
            return self._question_agent_payload(state, concept)
        if step["type"] == "homework":
            return self.transition_to_practice_phase(
                state,
                chapter={"title": state.current_chapter} if state.current_chapter else None,
                topic={"title": state.topic_title} if state.topic_title else None,
                concept={"title": state.concept_title} if state.concept_title else None,
                target="homework",
            )
        return {
            "type": "exam",
            "content": {
                "explanation": "You are ready for a short test.",
                "steps": [],
                "example": None,
                "voice_text": "You are ready for a short test.",
            },
        }

    def start_class(self, state: ClassroomState, grade: int = 10, subject: str = "math") -> None:
        self._set_active_phase(state, SessionPhase.TEACHING)
        curriculum = get_grade_curriculum(int(grade or 10))
        state.grade = int(grade or 10)
        state.curriculum = curriculum
        state.current_chapter_index = 0
        state.current_topic_index = 0
        state.current_concept_index = 0
        state.current_question_index = 0
        state.class_last_step = None
        state.class_phase = "teach"
        state.learning_path = []
        state.current_chapter = None
        state.current_topic = None
        state.current_concept = None
        state.exam_state = {}

        first_chapter = (curriculum.get("chapters") or [{}])[0]
        state.topic_slug = first_chapter.get("slug") or get_default_topic_slug(state.grade)
        state.topic_title = first_chapter.get("title") or "Mathematics"
        state.current_chapter = state.topic_title
        state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
        state.subject = subject or curriculum.get("subject", "math")
        state.cbse_outline = self._get_cbse_chapter_outline(first_chapter, state)
        state.completed_exercise_types = []
        state.completed_concepts = []
        state.current_exercise_type = None

    def _get_current_concept(self, state: ClassroomState) -> dict[str, Any]:
        curriculum = getattr(state, "curriculum", None) or get_grade_curriculum(state.grade)
        state.curriculum = curriculum
        chapters = curriculum.get("chapters") or []
        if not chapters:
            return {"chapter": None, "topic": None, "concept": None}

        chapter_index = min(max(getattr(state, "current_chapter_index", 0), 0), len(chapters) - 1)
        chapter = chapters[chapter_index]
        concepts = get_topic_concepts(state.grade, chapter.get("slug") or get_default_topic_slug(state.grade))
        if not concepts:
            return {"chapter": chapter, "topic": chapter, "concept": None}

        concept_index = min(max(getattr(state, "current_concept_index", 0), 0), len(concepts) - 1)
        concept = concepts[concept_index]

        state.current_chapter_index = chapter_index
        state.current_topic_index = 0
        state.current_concept_index = concept_index
        state.topic_slug = chapter.get("slug") or state.topic_slug
        state.topic_title = chapter.get("title") or state.topic_title
        state.concept_id = concept.get("id")
        state.concept_title = concept.get("title", "")
        state.current_chapter = state.topic_title
        state.current_topic = state.topic_slug
        state.current_concept = state.concept_title
        state.chapter_label = self._chapter_label(state.grade, state.topic_slug)

        return {"chapter": chapter, "topic": chapter, "concept": concept}

    def _class_response(
        self,
        *,
        response_type: str,
        state: ClassroomState,
        chapter: dict[str, Any] | None,
        topic: dict[str, Any] | None,
        concept: dict[str, Any] | None,
        explanation: str = "",
        steps: list[str] | None = None,
        question: str | None = None,
        correct: bool | None = None,
        hint: str | None = None,
        next_action: str = "continue",
        example: str | None = None,
        voice_text: str | None = None,
        analogy: str | None = None,
        check_question: str | None = None,
        pattern: str | None = None,
        shortcut: str | None = None,
        speed_hint: str | None = None,
        homework: list[dict[str, Any]] | None = None,
        session_notes: list[str] | None = None,
        whiteboard: dict[str, Any] | None = None,
        pace: str = "slow",
        pause_ms: int = 900,
    ) -> dict[str, Any]:
        normalized_type = response_type if response_type in {"teach", "board_example", "question", "evaluation", "homework", "chapter_complete", "exercise_solution"} else "evaluation"
        voice = sanitize_for_speech(voice_text or explanation)
        response = {
            "type": normalized_type,
            "chapter": chapter.get("title") if chapter else None,
            "chapter_label": state.chapter_label,
            "topic": topic.get("title") if topic else None,
            "concept": concept.get("title") if concept else None,
            "explanation": explanation,
            "steps": steps or [],
            "question": question,
            "correct": correct,
            "hint": hint,
            "next_action": next_action,
            "example": example,
            "analogy": analogy,
            "check_question": check_question,
            "voice_text": voice,
            "pattern": pattern,
            "shortcut": shortcut,
            "speed_hint": speed_hint,
            "whiteboard": whiteboard or dict(getattr(state, "whiteboard", {}) or {}),
            "homework": homework,
            "session_notes": session_notes or list(getattr(state, "session_notes", []) or []),
            "note_cards": list(getattr(state, "note_cards", []) or []),
            "pace": pace,
            "pause_ms": pause_ms,
            "avatar_voice": {
                "style": "math_tutor",
                "pace": pace,
                "sync_to_whiteboard": True,
                "pause_ms": pause_ms,
            },
        }
        response["avatar_stream"] = format_for_avatar(response)
        response["content"] = {
            "chapter": response["chapter"],
            "chapter_label": response["chapter_label"],
            "concept": response["concept"],
            "explanation": response["explanation"],
            "steps": response["steps"],
            "example": response["example"],
            "analogy": response["analogy"],
            "check_question": response["check_question"],
            "voice_text": response["voice_text"],
            "question": response["question"],
            "pattern": response["pattern"],
            "shortcut": response["shortcut"],
            "speed_hint": response["speed_hint"],
            "whiteboard": response["whiteboard"],
            "homework": response["homework"],
            "session_notes": response["session_notes"],
            "note_cards": response["note_cards"],
            "avatar_voice": response["avatar_voice"],
            "avatar_stream": response["avatar_stream"],
        }
        return response

    def _theory_welcome_response(self, state: ClassroomState) -> dict[str, Any]:
        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        topic_title = (
            (topic.get("title") if isinstance(topic, dict) else None)
            or getattr(state, "topic_title", None)
            or "this chapter"
        )
        explanation = f"Welcome to the class! Let's start with the theory for {topic_title}."
        state.class_last_step = "intro"
        state.stage = "TEACH"
        return self._class_response(
            response_type="teach",
            state=state,
            chapter=chapter,
            topic=topic,
            concept=concept,
            explanation=explanation,
            steps=[
                f"Topic: {topic_title}",
                "Step 1: Understand the core concept.",
                "Step 2: Build intuition with one simple example.",
            ],
            next_action="continue",
            voice_text=explanation,
        )

    def transition_to_practice_phase(
        self,
        state: ClassroomState,
        *,
        chapter: dict[str, Any] | None = None,
        topic: dict[str, Any] | None = None,
        concept: dict[str, Any] | None = None,
        target: str = "practice",
        practice_payload: dict[str, Any] | None = None,
        grade: int | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        self._set_active_phase(state, SessionPhase.PRACTICE)
        state.class_phase = "practice"
        state.stage = "PRACTICE"

        if target == "exercise":
            return self._teach_exercise_type(state)
        if target == "homework":
            return self._class_homework_response(state, chapter, topic, concept)
        if target == "pdf_exercises":
            return self._start_pdf_exercise_session(
                state,
                practice_payload or {"scope": "all_chapters"},
                int(grade or getattr(state, "grade", 10) or 10),
                subject or getattr(state, "subject", "math") or "math",
            )

        current = self._get_current_concept(state)
        return self._class_response(
            response_type="teach",
            state=state,
            chapter=current["chapter"],
            topic=current["topic"],
            concept=current["concept"],
            explanation="Practice phase is active. We can now solve exercises step by step.",
            steps=[],
            next_action="continue",
            voice_text="Practice phase is active. We can now solve exercises step by step.",
        )

    def _text_from_class_response(self, response: dict[str, Any]) -> str:
        if not isinstance(response, dict):
            return str(response)

        parts = [str(response.get("explanation") or "").strip()]
        question = response.get("question")
        if question:
            parts.append(f"Question: {question}")
        steps = [str(step).strip() for step in response.get("steps", []) if str(step).strip()]
        if steps:
            parts.append(self._format_list(steps))
        whiteboard = response.get("whiteboard") if isinstance(response.get("whiteboard"), dict) else {}
        answer = whiteboard.get("answer")
        if answer:
            parts.append(f"Answer: {answer}")
        next_action = response.get("next_action")
        if next_action == "next_exercise":
            parts.append("Say next exercise when you are ready.")
        return "\n\n".join(part for part in parts if part)

    def _teach_concept(self, state: ClassroomState) -> dict[str, Any]:
        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        if not chapter or not concept:
            chapter_title = getattr(state, "topic_title", None) or "Mathematics"
            explanation = (
                f"Welcome back. Today we will begin with theory for {chapter_title}. "
                "I will first explain the core concept in simple steps, then we will move to examples."
            )
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=chapter,
                topic=topic,
                concept=concept,
                explanation=explanation,
                steps=[],
                next_action="continue",
                voice_text=explanation,
            )

        question = self._concept_check_question(concept)
        state.class_last_step = "teach"
        state.stage = "TEACH"
        state.board_problem_phase = "ncert_examples"
        state.board_problem_index = 0
        state.learning_path.append({
            "chapter": chapter.get("title"),
            "topic": topic.get("title"),
            "concept_index": state.current_concept_index,
        })

        exam = _normalize_exam(getattr(state, "exam", "cbse"))
        example = self._concept_example(concept) or question.get("prompt")

        if exam == "jee":
            prompt = question.get("prompt") or example or concept.get("title", "")
            pattern = self._classify_jee_pattern(prompt)
            plan = self._build_jee_response({"prompt": prompt, "pattern": pattern}, "concept_error")
            pattern_title = pattern.replace("_", " ").title()
            shortcut = plan.get("shortcut") or "Identify the pattern first, then factor or use the formula."
            speed_hint = plan.get("speed_hint") or self._speed_hint("jee", None)
            steps = plan.get("concept_steps") or [
                f"Recognize: {pattern_title}",
                "Choose the fastest solving route.",
                "Check both roots mentally.",
            ]
            explanation = f"Pattern: {pattern_title}. Use the shortcut before doing long calculation."
            whiteboard = self._prepare_concept_board(state, topic, concept, question, mode="concept")
            notes = self._remember_session_notes(state, topic, concept, steps[:3])
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=chapter,
                topic=topic,
                concept=concept,
                explanation=explanation,
                steps=steps[:3],
                next_action="board_example",
                example=example,
                voice_text=self._slow_voice_text(state, concept, explanation, shortcut),
                pattern=pattern_title,
                shortcut=shortcut,
                speed_hint=speed_hint,
                whiteboard=whiteboard,
                session_notes=notes,
            )

        outline = getattr(state, "cbse_outline", {}) or self._get_cbse_chapter_outline(chapter, state)
        state.cbse_outline = outline
        check_question = self._generate_cbse_check_question(concept)
        state.active_problem = check_question
        state.attempts_on_problem = 0
        steps = concept.get("board_work", [])[:3] or [
            "Read the meaning first.",
            "Connect it with one small example.",
            "Check the answer carefully.",
        ]
        steps = [re.sub(r"^Step\s*\d+\s*:\s*", "", self._sentence(step)) for step in steps][:4]
        analogy = self._concept_analogy(concept)
        explanation = self._sentence(
            concept.get("explanation")
            or f"{concept.get('title', 'This idea')} tells us a simple rule. First we understand what the rule means. Then we use it in one easy example."
        )
        whiteboard = self._prepare_concept_board(state, topic, concept, question, mode="concept")
        whiteboard["chalk_lines"] = [
            f"Concept: {concept.get('title', 'Today topic')}",
            explanation,
            f"Analogy: {analogy}",
        ][:6]
        whiteboard["solution_steps"] = steps
        notes = self._remember_session_notes(state, topic, concept, [analogy, *steps])
        return self._class_response(
            response_type="teach",
            state=state,
            chapter=chapter,
            topic=topic,
            concept=concept,
            explanation=explanation,
            steps=steps,
            next_action="question",
            example=example,
            analogy=analogy,
            check_question=check_question.get("prompt"),
            voice_text=self._build_voice_text(f"{explanation} For example, {example or steps[-1]}. {analogy}", steps),
            whiteboard=whiteboard,
            session_notes=notes,
        )

    def _board_example(self, state: ClassroomState) -> dict[str, Any]:
        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        if not concept:
            return self._class_homework_response(state, chapter, topic, concept)

        board_problems = self._concept_board_problems(state, concept)
        index = min(max(getattr(state, "board_problem_index", 0), 0), max(len(board_problems) - 1, 0))
        problem = board_problems[index] if board_problems else (getattr(state, "active_problem", None) or self._concept_check_question(concept))
        state.active_problem = problem
        state.class_last_step = "board_example"
        state.board_problem_index = index
        steps = [
            str(step).strip() for step in problem.get("steps", []) if str(step).strip()
        ] or concept.get("board_work", [])[:3]
        whiteboard = self._prepare_concept_board(state, topic, concept, problem, mode="worked_example")
        source_label = "NCERT textbook example" if problem.get("source") == "ncert_example" else "NCERT exercise problem type"
        explanation = (
            f"Let us solve {source_label} {index + 1} of {len(board_problems) or 1} on the board before I ask you one. "
            f"Problem: {problem.get('prompt', self._concept_example(concept) or concept.get('title', 'example'))}"
        )
        notes = self._remember_session_notes(state, topic, concept, steps)
        next_action = "board_example" if index + 1 < len(board_problems) else "question"
        return self._class_response(
            response_type="board_example",
            state=state,
            chapter=chapter,
            topic=topic,
            concept=concept,
            explanation=explanation,
            steps=steps,
            next_action=next_action,
            example=problem.get("prompt"),
            voice_text=self._slow_voice_text(
                state,
                concept,
                explanation,
                "First copy the problem. Then follow each board step slowly. We will continue only after all textbook examples and exercise types for this concept are explained.",
            ),
            whiteboard=whiteboard,
            session_notes=notes,
        )

    def _mini_question(self, state: ClassroomState) -> dict[str, Any]:
        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        if not concept:
            return self._next_concept(state)

        if _normalize_exam(getattr(state, "exam", "cbse")) == "cbse":
            question = getattr(state, "active_problem", None) or self._generate_cbse_check_question(concept)
        else:
            question = self._concept_check_question(concept)
        state.active_problem = question
        state.class_last_step = "question"
        whiteboard = self._prepare_concept_board(state, topic, concept, question, mode="student_try")
        explanation = "Now you try one new mini check. It uses the same idea, but the numbers are different."
        return self._class_response(
            response_type="question",
            state=state,
            chapter=chapter,
            topic=topic,
            concept=concept,
            explanation=explanation,
            steps=[],
            question=question.get("prompt"),
            hint=question.get("hint"),
            next_action="evaluate",
            check_question=question.get("prompt"),
            voice_text=self._build_voice_text(explanation, []),
            whiteboard=whiteboard,
        )

    def _evaluate_class_answer(self, state: ClassroomState, answer: Any) -> dict[str, Any]:
        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        question = getattr(state, "active_problem", None) or (self._concept_check_question(concept) if concept else {})

        accepted_answers = question.get("accepted_answers") or []
        expected = question.get("answer")
        submitted = str(answer or "").strip()
        if accepted_answers:
            correct = submitted.lower() in {str(item).strip().lower() for item in accepted_answers}
            mistake_type = None if correct else "concept_error"
        elif expected is not None and question.get("answer_type") == "text":
            correct = submitted.lower() == str(expected).strip().lower()
            mistake_type = None if correct else "concept_error"
        else:
            result = self._evaluate_homework_answer(question, submitted)
            correct = bool(result.get("correct"))
            mistake_type = result.get("mistake_type")

        state.stats = getattr(state, "stats", _default_stats())
        state.stats.setdefault("by_mistake", {})
        state.stats.setdefault("by_topic", {})
        state.stats.setdefault("by_pattern", {})
        topic_key = topic.get("title", "Unknown") if topic else "Unknown"
        if correct:
            state.stats["correct"] = state.stats.get("correct", 0) + 1
        else:
            state.stats["wrong"] = state.stats.get("wrong", 0) + 1
            if mistake_type:
                state.stats["by_mistake"][mistake_type] = state.stats["by_mistake"].get(mistake_type, 0) + 1
            state.stats["by_topic"].setdefault(topic_key, {"correct": 0, "wrong": 0})
            state.stats["by_topic"][topic_key]["wrong"] += 1
        state.stats["total"] = state.stats.get("total", 0) + 1

        if correct:
            state.attempts_on_problem = 0
            if getattr(state, "current_exercise_type", None):
                state.completed_exercise_types = list(dict.fromkeys([
                    *getattr(state, "completed_exercise_types", []),
                    state.current_exercise_type,
                ]))
                state.current_exercise_type = None
            if concept and concept.get("id"):
                state.completed_concepts = list(dict.fromkeys([*getattr(state, "completed_concepts", []), concept["id"]]))
            state.class_last_step = "evaluation"
            next_result = self._next_concept(state)
            if next_result.get("type") == "chapter_complete":
                return self.transition_to_practice_phase(
                    state,
                    chapter=chapter,
                    topic=topic,
                    concept=concept,
                    target="homework",
                )
            if next_result.get("type") == "exercise":
                return self.transition_to_practice_phase(
                    state,
                    chapter=chapter,
                    topic=topic,
                    concept=concept,
                    target="exercise",
                )
            return self._class_response(
                response_type="evaluation",
                state=state,
                chapter=chapter,
                topic=topic,
                concept=concept,
                explanation="Correct. The next concept is ready.",
                steps=[],
                question=question.get("prompt"),
                correct=True,
                hint=None,
                next_action=next_result.get("next_action", "continue"),
                voice_text="Correct. Pause for a moment. Next, I will explain the next concept slowly on the board.",
            )

        state.attempts_on_problem = int(getattr(state, "attempts_on_problem", 0) or 0) + 1
        simpler = (
            "Not yet. Let us make it simpler. The main idea is to use the same rule on a smaller question first, "
            "then come back to this one."
        )
        if state.attempts_on_problem >= 2:
            state.attempts_on_problem = 0
            next_result = self._next_concept(state)
            if next_result.get("type") == "exercise":
                return self.transition_to_practice_phase(
                    state,
                    chapter=chapter,
                    topic=topic,
                    concept=concept,
                    target="exercise",
                )
            return self._class_response(
                response_type="evaluation",
                state=state,
                chapter=chapter,
                topic=topic,
                concept=concept,
                explanation=simpler,
                steps=[
                    "Read the question again.",
                    "Write the one rule needed.",
                    "Try one smaller version before the next concept.",
                ],
                question=question.get("prompt"),
                correct=False,
                hint=question.get("hint") or "Use the rule from the example.",
                next_action=next_result.get("next_action", "continue"),
                analogy=self._concept_analogy(concept or {}),
                voice_text=self._build_voice_text(simpler, ["Read the question again.", "Use one rule.", "Try a smaller version."]),
            )

        state.class_last_step = "teach"
        attempts = state.attempts_on_problem
        reteach = self._teach_concept(state)
        state.attempts_on_problem = attempts
        reteach["type"] = "evaluation"
        reteach["correct"] = False
        reteach["mistake_type"] = mistake_type
        reteach["hint"] = question.get("hint") or "Review the method and try the mini check again."
        reteach["next_action"] = "reteach"
        reteach["question"] = question.get("prompt")
        return reteach

    def _chapter_exercise_types(self, state: ClassroomState) -> list[str]:
        outline = getattr(state, "cbse_outline", {}) or {}
        exercise_types: list[str] = []
        for section in outline.get("sections", []):
            if isinstance(section, dict):
                exercise_types.extend(str(item) for item in section.get("exercise_types", []) if str(item).strip())
        if exercise_types:
            return [item for item in dict.fromkeys(exercise_types)][:6]

        current = self._get_current_concept(state)
        chapter = current["chapter"]
        concepts = get_topic_concepts(state.grade, chapter.get("slug") or get_default_topic_slug(state.grade)) if chapter else []
        for concept in concepts:
            for problem in concept.get("exercise_problems", []):
                if isinstance(problem, dict):
                    exercise_types.append(problem.get("type") or problem.get("prompt", "Exercise problem"))
        return [item for item in dict.fromkeys(self._sentence(item) for item in exercise_types if self._sentence(item))][:6]

    def _next_pending_exercise_type(self, state: ClassroomState) -> str | None:
        completed = set(getattr(state, "completed_exercise_types", []) or [])
        for exercise_type in self._chapter_exercise_types(state):
            if exercise_type not in completed:
                return exercise_type
        return None

    def _teach_exercise_type(self, state: ClassroomState) -> dict[str, Any]:
        if not self._is_practice_phase(state):
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )

        current = self._get_current_concept(state)
        chapter = current["chapter"]
        topic = current["topic"]
        concept = current["concept"]
        exercise_type = getattr(state, "current_exercise_type", None) or self._next_pending_exercise_type(state)
        if not exercise_type:
            return self._teach_concept(state)

        state.current_exercise_type = exercise_type
        state.class_last_step = "exercise_teach"
        question = self._generate_cbse_check_question(concept or {"title": exercise_type})
        question["prompt"] = f"Practice this exercise type with new numbers: {question.get('prompt', exercise_type)}"
        state.active_problem = question
        state.attempts_on_problem = 0

        explanation = f"This exercise type asks us to use the concept in a question. We first identify what is given, then apply the rule slowly."
        steps = [
            "Underline what is given.",
            "Choose the rule from the concept.",
            "Solve one small example.",
            "Check the answer once.",
        ]
        whiteboard = self._prepare_concept_board(state, topic, concept, question, mode="worked_example")
        whiteboard["subtitle"] = "Exercise type practice"
        return self._class_response(
            response_type="teach",
            state=state,
            chapter=chapter,
            topic=topic,
            concept=concept,
            explanation=explanation,
            steps=steps,
            next_action="question",
            example=exercise_type,
            analogy="Think of this as the same recipe in a new dish. The rule is the recipe, and the numbers are the ingredients.",
            check_question=question.get("prompt"),
            voice_text=self._build_voice_text(explanation, steps),
            whiteboard=whiteboard,
            session_notes=self._remember_session_notes(state, topic, concept, [f"Exercise type covered: {exercise_type}"]),
        )

    def _next_concept(self, state: ClassroomState) -> dict[str, Any]:
        curriculum = getattr(state, "curriculum", None) or get_grade_curriculum(state.grade)
        chapters = curriculum.get("chapters") or []
        if not chapters:
            state.class_last_step = "chapter_complete"
            return {"type": "chapter_complete", "message": "Chapter completed", "next_action": "test"}

        chapter = chapters[min(state.current_chapter_index, len(chapters) - 1)]
        concepts = get_topic_concepts(state.grade, chapter.get("slug") or get_default_topic_slug(state.grade))
        if state.current_concept_index + 1 < len(concepts):
            state.current_concept_index += 1
            state.class_last_step = "evaluation"
            return {"type": "continue", "next_action": "continue"}

        pending_exercise = self._next_pending_exercise_type(state)
        if _normalize_exam(getattr(state, "exam", "cbse")) == "cbse" and pending_exercise:
            state.current_exercise_type = pending_exercise
            state.class_last_step = "evaluation"
            return {"type": "exercise", "next_action": "continue"}

        if state.current_chapter_index + 1 < len(chapters):
            state.current_chapter_index += 1
            state.current_topic_index = 0
            state.current_concept_index = 0
            next_chapter = chapters[state.current_chapter_index]
            state.topic_slug = next_chapter.get("slug")
            state.topic_title = next_chapter.get("title")
            state.cbse_outline = self._get_cbse_chapter_outline(next_chapter, state)
            state.completed_exercise_types = []
            state.class_last_step = "evaluation"
            return {"type": "continue", "next_action": "continue"}

        state.class_last_step = "chapter_complete"
        return {"type": "chapter_complete", "message": "Chapter completed", "next_action": "test"}

    def run_class(self, state, input_data):
        data = input_data if isinstance(input_data, dict) else {}
        action = data.get("action")
        answer = data.get("answer")
        grade = int(data.get("grade") or getattr(state, "grade", 10) or 10)
        subject = data.get("subject") or "math"

        practice_actions = {
            "solve_pdf_exercises",
            "solve_all_exercises",
            "solve_all_pdf_exercises",
            "next_exercise",
            "next_pdf_exercise",
            "skip_homework",
            "end",
            "end_day",
            "homework",
            "finish",
        }
        if action in practice_actions and not self._is_practice_phase(state):
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )

        if action in {"solve_pdf_exercises", "solve_all_exercises", "solve_all_pdf_exercises"}:
            return self.transition_to_practice_phase(
                state,
                target="pdf_exercises",
                practice_payload=data,
                grade=grade,
                subject=subject,
            )

        if action in {"next_exercise", "next_pdf_exercise"}:
            return self._next_pdf_exercise_response(state)

        if action == "next" and getattr(state, "class_last_step", None) == "pdf_exercise":
            return self._next_pdf_exercise_response(state)

        if action == "skip_homework":
            return self._skip_homework_response(state)

        if action in {"end", "end_day", "homework", "finish"}:
            current = self._get_current_concept(state)
            state.class_last_step = "chapter_complete"
            return self.transition_to_practice_phase(
                state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                target="homework",
            )

        if action == "start" or not getattr(state, "curriculum", None) or getattr(state, "class_last_step", None) is None:
            self.start_class(state, grade, subject)
            self._set_active_phase(state, SessionPhase.TEACHING)
            return self._theory_welcome_response(state)

        if getattr(state, "class_last_step", None) == "intro":
            return self._teach_concept(state)

        if getattr(state, "class_last_step", None) == "teach":
            if _normalize_exam(getattr(state, "exam", "cbse")) == "cbse":
                return self._mini_question(state)
            return self._board_example(state)

        if getattr(state, "class_last_step", None) == "exercise_teach":
            return self._mini_question(state)

        if getattr(state, "class_last_step", None) == "board_example":
            current = self._get_current_concept(state)
            concept = current["concept"]
            board_problems = self._concept_board_problems(state, concept) if concept else []
            if getattr(state, "board_problem_index", 0) + 1 < len(board_problems):
                state.board_problem_index += 1
                return self._board_example(state)
            return self._mini_question(state)

        if getattr(state, "class_last_step", None) == "question":
            if answer is None:
                return self._mini_question(state)
            return self._evaluate_class_answer(state, answer)

        if getattr(state, "class_last_step", None) == "chapter_complete":
            current = self._get_current_concept(state)
            return self.transition_to_practice_phase(
                state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                target="homework",
            )

        return self._teach_concept(state)

    def _start_pdf_exercise_session(
        self,
        state: ClassroomState,
        data: dict[str, Any],
        grade: int,
        subject: str,
    ) -> dict[str, Any]:
        if not self._is_practice_phase(state):
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )

        if not getattr(state, "curriculum", None):
            curriculum = get_grade_curriculum(int(grade or 10))
            state.grade = int(grade or 10)
            state.curriculum = curriculum
            state.subject = subject or curriculum.get("subject", "math")
            first_chapter = (curriculum.get("chapters") or [{}])[0]
            state.topic_slug = first_chapter.get("slug") or get_default_topic_slug(state.grade)
            state.topic_title = first_chapter.get("title") or "Mathematics"
            state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
            state.current_chapter_index = 0
            state.current_topic_index = 0
            state.current_concept_index = 0

        curriculum = getattr(state, "curriculum", None) or get_grade_curriculum(grade)
        chapters = curriculum.get("chapters") or []
        scope = str(data.get("scope") or "all_chapters").lower()

        if scope in {"chapter", "current_chapter", "current"}:
            current = self._get_current_concept(state)
            chapter = current["chapter"] or (chapters[0] if chapters else {})
            fallback_index = int(getattr(state, "current_chapter_index", 0) or 0) + 1
            chapter_index = get_pdf_chapter_number(grade, chapter, fallback_index)
            problems = load_chapter_pdf_exercises(grade, chapter_index, chapter.get("title", f"Chapter {chapter_index}"))
        else:
            problems = load_all_pdf_exercises(grade, chapters)

        state.pdf_exercise_session = {
            "scope": scope,
            "index": 0,
            "total": len(problems),
            "problems": problems,
        }
        state.class_last_step = "pdf_exercise"

        if not problems:
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="exercise_solution",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation="I could not find readable exercise questions in the local CBSE PDF files for this scope.",
                steps=[],
                next_action="continue",
                voice_text="I could not find readable exercise questions in the local CBSE PDF files for this scope.",
                whiteboard={
                    "mode": "pdf_exercise",
                    "title": "CBSE PDF Exercises",
                    "subtitle": "No readable exercises found",
                    "solution_steps": [],
                },
            )

        return self._pdf_exercise_response_at_cursor(state)

    def _next_pdf_exercise_response(self, state: ClassroomState) -> dict[str, Any]:
        if not self._is_practice_phase(state):
            current = self._get_current_concept(state)
            return self._class_response(
                response_type="teach",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation=self.PRACTICE_GATE_MESSAGE,
                steps=[],
                next_action="continue",
                voice_text=self.PRACTICE_GATE_MESSAGE,
            )

        session = getattr(state, "pdf_exercise_session", {}) or {}
        problems = session.get("problems") or []
        if not problems:
            return self._start_pdf_exercise_session(state, {"scope": "all_chapters"}, getattr(state, "grade", 10), "math")

        session["index"] = int(session.get("index") or 0) + 1
        state.pdf_exercise_session = session
        if session["index"] >= len(problems):
            current = self._get_current_concept(state)
            state.class_last_step = "chapter_complete"
            return self._class_response(
                response_type="chapter_complete",
                state=state,
                chapter=current["chapter"],
                topic=current["topic"],
                concept=current["concept"],
                explanation="All readable CBSE PDF exercise questions in this scope have been covered on the whiteboard.",
                steps=[],
                next_action="homework",
                voice_text="All readable CBSE PDF exercise questions in this scope have been covered on the whiteboard.",
                whiteboard={
                    "mode": "pdf_exercise_complete",
                    "title": "CBSE PDF Exercises",
                    "subtitle": "Complete",
                    "solution_steps": ["All readable PDF exercises in this scope are complete."],
                },
            )

        return self._pdf_exercise_response_at_cursor(state)

    def _pdf_exercise_response_at_cursor(self, state: ClassroomState) -> dict[str, Any]:
        session = getattr(state, "pdf_exercise_session", {}) or {}
        problems = session.get("problems") or []
        index = min(max(int(session.get("index") or 0), 0), max(len(problems) - 1, 0))
        raw_problem = problems[index]
        # Pass session_id and current chapter context to prevent context loss between turns
        session_id = getattr(state, "session_id", None)
        current_chapter = getattr(state, "topic_title", None) or getattr(state, "chapter_name", None)
        problem = build_exercise_solution(raw_problem, session_id=session_id, current_chapter=current_chapter)

        chapters = (getattr(state, "curriculum", None) or get_grade_curriculum(state.grade)).get("chapters") or []
        chapter_title = str(problem.get("chapter_title") or "")
        chapter_index = next(
            (idx for idx, item in enumerate(chapters) if str(item.get("title") or "") == chapter_title),
            max(int(problem.get("chapter_index") or 1) - 1, 0),
        )
        chapter = chapters[chapter_index] if chapter_index < len(chapters) else {
            "title": problem.get("chapter_title"),
            "slug": state.topic_slug,
        }
        state.current_chapter_index = chapter_index
        state.topic_slug = chapter.get("slug") or state.topic_slug
        state.topic_title = chapter.get("title") or problem.get("chapter_title") or state.topic_title
        state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
        concept = self._get_current_concept(state).get("concept")

        steps = [str(step).strip() for step in problem.get("steps", []) if str(step).strip()]
        progress = f"{index + 1} of {len(problems)}"
        whiteboard = {
            "mode": "pdf_exercise",
            "title": problem.get("chapter_title") or state.topic_title or "CBSE PDF Exercises",
            "subtitle": f"{problem.get('exercise')} Q{problem.get('number')} · {progress}",
            "problem": problem.get("prompt"),
            "solution_steps": steps,
            "answer": problem.get("answer"),
            "source_file": problem.get("source_file"),
        }
        state.whiteboard = whiteboard
        state.active_problem = problem
        state.class_last_step = "pdf_exercise"

        explanation = (
            f"Now we will solve {problem.get('exercise')} question {problem.get('number')} from "
            f"{problem.get('chapter_title')}. First, let us read the question carefully: {problem.get('prompt')}. "
            "Let me explain the solution step by step."
        )
        response = self._class_response(
            response_type="exercise_solution",
            state=state,
            chapter=chapter,
            topic=chapter,
            concept=concept,
            explanation=explanation,
            steps=steps,
            question=problem.get("prompt"),
            next_action="next_exercise",
            example=problem.get("prompt"),
            voice_text=self._slow_voice_text(
                state,
                concept,
                explanation,
                "Say next exercise when you are ready for the next PDF problem.",
            ),
            whiteboard=whiteboard,
            session_notes=self._remember_session_notes(state, chapter, concept, steps[:3]),
        )
        voice_chunks = steps + ([f"Final answer: {problem.get('answer')}"] if problem.get("answer") else [])
        response["voice_text"] = " ".join(voice_chunks)
        response["avatar_stream"] = {
            "voice_chunks": voice_chunks,
            "steps": steps,
            "pace": "slow",
            "pause_ms": 900,
        }
        response["content"]["voice_text"] = response["voice_text"]
        response["content"]["avatar_stream"] = response["avatar_stream"]
        return response

    def handle_homework(self, state, text):
        payload = text if isinstance(text, dict) else {}
        action = payload.get("action") if isinstance(payload, dict) else None
        answers = payload.get("answers") if isinstance(payload, dict) else None
        topic = payload.get("topic") if isinstance(payload, dict) else text

        if not self._is_practice_phase(state):
            return {
                "score": None,
                "weak_areas": [],
                "explanation": self.PRACTICE_GATE_MESSAGE,
                "questions": [],
                "next_recommendation": "Continue with theory first.",
            }

        if action in {"help", "unable", "not_able"}:
            questions = getattr(state, "homework_questions", []) or self.generate_homework(state, topic)
            index = int(payload.get("question_index") or 0)
            question_from_payload = payload.get("question_data") if isinstance(payload.get("question_data"), dict) else None
            if question_from_payload:
                question = dict(question_from_payload)
            elif index < 0 or index >= len(questions):
                return {"error": "Homework question not found.", "type": "homework_help"}
            else:
                question = questions[index]
            steps = [str(step).strip() for step in question.get("steps", []) if str(step).strip()]
            if not steps:
                hint = question.get("hint")
                steps = [
                    f"Read the question carefully: {question.get('prompt') or question.get('question') or 'homework problem'}",
                    *( [f"Use the hint: {hint}"] if hint else [] ),
                    "Write the known values and apply the concept from today's board work.",
                    f"Final answer: {self._format_expected_answer(question)}",
                ]
            whiteboard = {
                "mode": "homework_help",
                "title": question.get("topic") or state.topic_title or "Homework",
                "subtitle": question.get("concept") or "Step-by-step solution",
                "problem": question.get("prompt") or question.get("question"),
                "solution_steps": steps,
                "answer": self._format_expected_answer(question),
            }
            return {
                "type": "homework_help",
                "explanation": "No problem. Let us solve this homework sum slowly on the whiteboard.",
                "question": question,
                "steps": steps,
                "whiteboard": whiteboard,
                "voice_text": self._slow_voice_text(
                    state,
                    {"title": question.get("concept") or "Homework help"},
                    "No problem. Let us solve this homework sum slowly on the whiteboard.",
                    "Copy one step at a time, then try the next similar sum yourself.",
                ),
                "avatar_stream": format_for_avatar({"voice_text": "No problem. Let us solve this homework sum slowly on the whiteboard.", "steps": steps}),
            }

        if answers:
            questions = getattr(state, "homework_questions", [])
            score = 0
            weak_areas = []
            help_solutions = []
            for index, answer in enumerate(answers):
                if index >= len(questions):
                    continue
                if str(answer or "").strip().lower() in {"not able", "not able to solve", "unable", "skip", "__unable__"}:
                    weak_areas.append("needs_homework_help")
                    question = questions[index]
                    help_solutions.append({
                        "index": index,
                        "question": question.get("prompt") or question.get("question"),
                        "steps": question.get("steps", []),
                        "answer": self._format_expected_answer(question),
                    })
                    continue
                result = self._evaluate_homework_answer(questions[index], str(answer))
                score += 1 if result["correct"] else 0
                if result["mistake_type"]:
                    weak_areas.append(result["mistake_type"])
            next_class = self._advance_after_homework(state)
            return {
                "score": score,
                "weak_areas": list(dict.fromkeys(weak_areas)),
                "explanation": "Homework evaluated.",
                "help_solutions": help_solutions,
                "next_recommendation": "Practice weak areas again." if weak_areas else "Move to the next concept.",
                "next_class": next_class,
                "next_topic": next_class.get("topic") or next_class.get("chapter"),
                "next_concept": next_class.get("concept"),
            }

        questions = self.generate_homework(state, topic)
        state.homework_questions = questions
        return {
            "score": None,
            "weak_areas": [],
            "explanation": "Homework generated.",
            "questions": questions,
            "next_recommendation": "Submit answers when ready.",
        }
