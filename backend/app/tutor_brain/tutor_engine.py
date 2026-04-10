from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

from .curriculum import find_topic_by_message, get_concept, get_default_topic_slug, get_next_concept, get_topic
from .lesson_state import LessonState


class TutorEngine:
    def __init__(self):
        self.sessions: dict[str, LessonState] = {}
        self.ready_keywords = [
            "ready",
            "start",
            "begin",
            "continue",
            "let's go",
            "lets go",
            "i am ready",
            "i'm ready",
            "can we start",
            "start the lesson",
        ]
        self.break_keywords = ["pause", "stop", "break", "rest"]
        self.practice_keywords = [
            "practice",
            "quiz",
            "problem",
            "exercise",
            "test me",
            "ask me a question",
            "give me a question",
            "let me try",
            "one more",
        ]
        self.revision_keywords = ["revise", "review", "summary", "recap", "go over", "repeat"]
        self.greeting_keywords = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        self.math_keywords = [
            "math",
            "mathematics",
            "equation",
            "algebra",
            "triangle",
            "trigonometry",
            "coordinate",
            "circle",
            "probability",
            "statistics",
            "volume",
            "linear",
            "solve",
            "graph",
            "variable",
            "number",
        ]

    def _state_for(self, session_id: str) -> LessonState:
        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()
        return self.sessions[session_id]

    def hydrate_session(self, session_id: str, session_record=None) -> LessonState:
        state = self._state_for(session_id)
        if not session_record:
            return state
retriever = None
retriever_lock = Lock()


def _embedding_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings
    except ImportError:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"The class `HuggingFaceEmbeddings` was deprecated in LangChain")
            from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings


def init_cbse() -> None:
    global retriever
    if retriever is not None:
        return

    with retriever_lock:
        if retriever is not None:
            return

        print("Loading CBSE FAISS index...")
        try:
            from langchain_community.vectorstores import FAISS

            embeddings_cls = _embedding_class()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r"The class `HuggingFaceEmbeddings` was deprecated in LangChain")
                embeddings = embeddings_cls(model_name="sentence-transformers/all-MiniLM-L6-v2")

            vectorstore = FAISS.load_local(
                "backend/data/faiss_index",
                embeddings,
                allow_dangerous_deserialization=True,
            )
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            print("CBSE index loaded")
        except Exception as error:
            print(f"CBSE init failed: {error}")


@dataclass
class ClassroomState:
    grade: int = 10
    stage: str = "INTRO"
    topic_slug: str | None = None
    topic_title: str | None = None
    concept_id: str | None = None
    concept_title: str = ""
    summary: str = ""
    note_cards: list[str] = field(default_factory=list)
    whiteboard: dict[str, Any] = field(default_factory=dict)
    current_question_index: int = 0
    active_problem: dict[str, Any] | None = None
    attempts_on_problem: int = 0


class TutorEngine:
    def __init__(self) -> None:
        self._states: dict[str, ClassroomState] = {}
        self._state_lock = Lock()

    def hydrate_session(self, session_id, session) -> None:
        with self._state_lock:
            state = self._states.get(session_id)
            if state is None:
                state = self._fresh_state(getattr(session, "grade", 10), getattr(session, "topic_slug", None))
                self._states[session_id] = state

            state.grade = getattr(session, "grade", state.grade)
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
            if getattr(session, "lesson_notes", None):
                state.note_cards = list(session.lesson_notes[:6])
            if getattr(session, "summary", None):
                state.summary = session.summary
            state.active_problem = self._current_problem(state)
            print("Hydrated classroom state")

    def process(self, session_id: str, message: str, session_record=None) -> str:
        state = self._ensure_state(session_id, session_record)
        text = (message or "").strip()
        if not text:
            return self._build_intro(state)

        lowered = text.lower()
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

        if state.active_problem and any(token in lowered for token in ["hint", "clue"]):
            return self._give_hint(state)
        if state.active_problem and any(token in lowered for token in ["solution", "steps", "solve it", "show answer"]):
            return self._show_solution(state)
        if any(token in lowered for token in ["practice", "quiz", "test me", "ask me a question"]):
            return self._offer_practice(state)
        if any(token in lowered for token in ["ready", "start", "begin", "continue", "next", "go on", "teach from basics"]):
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
        )

    def extract_number(self, message: str) -> float | None:
        numbers = re.findall(r"-?\d+\.?\d*", message)
        if not numbers:
            return None
        return float(numbers[0])

    def extract_pair(self, message: str) -> tuple[float, float] | None:
        numbers = re.findall(r"-?\d+\.?\d*", message)
        if len(numbers) < 2:
            return None
        return float(numbers[0]), float(numbers[1])

    def _ensure_topic(self, state: LessonState) -> dict:
        if not state.topic_slug:
            state.topic_slug = get_default_topic_slug(state.grade)

        topic = get_topic(state.grade, state.topic_slug)
        if topic:
            state.topic_title = topic["title"]
        else:
            topic = get_topic(state.grade, get_default_topic_slug(state.grade))
            state.topic_slug = topic["slug"]
            state.topic_title = topic["title"]

        return topic

    def _ensure_concept(self, state: LessonState) -> dict | None:
        topic = self._ensure_topic(state)
        concept = get_concept(state.grade, topic["slug"], state.current_concept_id or None)
        if concept:
            state.current_concept = concept
            state.current_concept_id = concept["id"]
            state.current_concept_title = concept["title"]
        return concept

    def _switch_topic(self, state: LessonState, topic: dict) -> None:
        state.topic_slug = topic["slug"]
        state.topic_title = topic["title"]
        state.step = "TOPIC_INTRODUCTION"
        state.current_concept_id = ""
        state.current_concept_title = ""
        state.current_concept = None
        state.current_question_index = 0
        state.correct_answers_in_concept = 0
        state.homework_given = False
        state.notes = [
            f"Topic switched to {topic['title']}.",
            topic.get("summary", ""),
        ]
        state.last_summary = f"Switched to {topic['title']} for guided teaching."

    def _chapter_menu(self, grade: int) -> str:
        chapters = list_chapters(grade)
        return "\n".join(f"- {chapter['title']}" for chapter in chapters)

    def _lesson_timing_line(self, state: LessonState) -> str:
        pace_map = {
            "INTRO": (0, 45),
            "TOPIC_INTRODUCTION": (5, 40),
            "GUIDED_EXPLANATION": (15, 30),
            "PRACTICE": (30, 15),
            "REFLECTION": (40, 5),
        }
        elapsed, remaining = pace_map.get(state.step, (20, 25))
        return f"Class plan: 45 minutes total. About {elapsed} minutes done and {remaining} minutes left."

    def _build_intro(self, state: LessonState, session_record=None) -> str:
        topic = self._ensure_topic(state)
        state.step = "TOPIC_INTRODUCTION"
        state.notes = [
            f"Board: CBSE Class {state.grade} Mathematics",
            f"Focus chapter: {topic['title']}",
            topic.get("classroom_goal", topic.get("summary", "")),
        ]
        state.last_summary = f"Started a guided class on {topic['title']}."

        student_label = "there"
        if session_record and session_record.student_id:
            student_label = session_record.student_id.replace("-", " ")

        return (
            f"Hi {student_label}. I'm Ava, and today we'll work on {topic['title']} for Class {state.grade}.\n\n"
            "I will teach strictly from the loaded CBSE NCERT chapter map for your class, with grounded examples only.\n\n"
            f"For Class {state.grade}, our NCERT chapter list is:\n{self._chapter_menu(state.grade)}\n\n"
            f"By the end of this lesson, you should feel comfortable with {topic.get('classroom_goal', topic.get('summary', 'the main idea of this chapter'))}.\n\n"
            f"{self._lesson_timing_line(state)}\n"
            "We'll keep a moderate pace with small pauses between ideas so the explanation stays clear.\n\n"
            "You can reply naturally, for example: let's start, explain again, give me a question, or I need a hint."
    def generate_response(self, message: str, state: Optional[LessonState] = None) -> str:
        return self.process("stateless", message)

    def _ensure_state(self, session_id: str, session_record=None) -> ClassroomState:
        with self._state_lock:
            state = self._states.get(session_id)
            if state is not None:
                if session_record is not None:
                    state.grade = getattr(session_record, "grade", state.grade)
                return state

            grade = getattr(session_record, "grade", 10) if session_record is not None else 10
            topic_slug = getattr(session_record, "topic_slug", None) if session_record is not None else None
            state = self._fresh_state(grade, topic_slug)
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
        )
        self._refresh_public_state(state, include_problem=False)
        return state

    def _set_topic(self, state: ClassroomState, grade: int, topic_slug: str, reset: bool) -> None:
        topic = get_topic(grade, topic_slug)
        concept = get_concept(grade, topic_slug)
        state.grade = grade
        state.topic_slug = topic_slug
        state.topic_title = topic["title"] if topic else topic_slug.replace("_", " ").title()
        state.concept_id = concept["id"] if concept else None
        state.concept_title = concept["title"] if concept else ""
        if reset:
            state.stage = "INTRO"
            state.current_question_index = 0
            state.active_problem = None
            state.attempts_on_problem = 0
        self._refresh_public_state(state, include_problem=False)

    def _advance(self, state: ClassroomState) -> str:
        if state.stage == "INTRO":
            return self._teach_current_concept(state, transition=False)
        if state.active_problem:
            return self._restate_problem(state)
        return self._teach_current_concept(state, transition=True)

    def _build_intro(self, state: ClassroomState) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        self._refresh_public_state(state, include_problem=False)
        chapter = topic["title"] if topic else state.topic_title or "the current chapter"
        first_concept = concept["title"] if concept else "the basics"
        return (
            "Welcome back.\n\n"
            f"Last time we were working on {topic['title']} in Class {state.grade}. "
            f"Our last checkpoint was: {session_record.summary or 'we are ready to continue.'}\n\n"
            f"I remember what we covered from your saved notes, and I'll continue from that exact point. {self._lesson_timing_line(state)}\n\n"
            "If you want, we can continue from there, do a quick revision, or switch chapters."
        )

    def _build_guided_explanation(self, state: LessonState) -> str:
        topic = self._ensure_topic(state)
        concept = self._ensure_concept(state)
        state.step = "GUIDED_EXPLANATION"

        if not concept:
            state.notes = [
                f"Discussing {topic['title']}.",
                topic.get("summary", "Concept discussion in progress."),
            ]
            state.last_summary = f"Guided explanation in progress for {topic['title']}."
            return (
                f"Let's start with {topic['title']}.\n\n"
                "We'll take one idea at a time at moderate-to-slow speed, with pauses after each step.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will build the idea step by step.'))}\n\n"
                f"{self._lesson_timing_line(state)} Ask a doubt any time, or ask for a guided question."
            )

        board_steps = concept.get("board_work", [])[:3]
        board_script = " ".join(board_steps) if board_steps else "We will solve a simple example together."
        state.notes = [
            f"Concept: {concept['title']}",
            topic.get("teaching_anchor", topic.get("summary", "")),
            "Next move: guided practice.",
        ]
        state.last_summary = f"Explaining {concept['title']} in {topic['title']}."
            f"Welcome back. Today we are starting {chapter}.\n\n"
            f"We will do this like a classroom: first {first_concept.lower()}, then one board example, then one short question for you.\n\n"
            "Say ready when you want me to begin."
        )

    def _build_topic_switch_response(self, state: ClassroomState) -> str:
        return (
            f"Sure. We are switching to {state.topic_title}.\n\n"
            "I will teach it in classroom order: idea first, board example next, and then a quick check from you.\n\n"
            "Say ready when you want me to begin."
        )

    def _teach_current_concept(self, state: ClassroomState, transition: bool) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if not topic or not concept:
            state.summary = "The class is ready, but the chapter selection needs to be clarified."
            return "Tell me the chapter name you want to study, and I will teach it from the basics."

        state.stage = "CHECK"
        state.concept_id = concept["id"]
        state.concept_title = concept["title"]
        state.current_question_index = 0
        state.active_problem = self._current_problem(state)
        state.attempts_on_problem = 0
        self._refresh_public_state(state, include_problem=True)

        board_work = concept.get("board_work", [])
        parts = []
        parts.append("Good. Let us start properly." if not transition else "Good. Now let us move to the next classroom idea.")
        parts.append(f"Today our focus is {concept['title']} in {topic['title']}.")
        parts.append(concept.get("explanation", topic.get("summary", "")))
        if topic.get("teaching_anchor"):
            parts.append(f"Key idea: {topic['teaching_anchor']}")
        if board_work:
            parts.append(f"On the board, look at this: {board_work[0]}")
        if state.active_problem:
            parts.append(f"Now your turn: {state.active_problem['prompt']}")
            parts.append("Answer briefly, and I will guide the next step.")
        return "\n\n".join(part for part in parts if part)

    def _offer_practice(self, state: ClassroomState) -> str:
        if state.active_problem is None:
            state.active_problem = self._current_problem(state)
            state.attempts_on_problem = 0
        state.stage = "PRACTICE"
        self._refresh_public_state(state, include_problem=True)
        return self._restate_problem(state)

    def _restate_problem(self, state: ClassroomState) -> str:
        if not state.active_problem:
            return "I do not have a class question ready yet. Say ready, and I will start a guided example first."
        hint = state.active_problem.get("hint")
        parts = ["Your turn now.", state.active_problem["prompt"]]
        if hint and state.attempts_on_problem > 0:
            parts.append(f"Hint: {hint}")
        parts.append("Give only the answer first. If you want, you can also ask for a hint.")
        return "\n\n".join(parts)

    def _handle_answer(self, state: ClassroomState, message: str) -> str:
        problem = state.active_problem
        if not problem:
            return self._answer_like_teacher(state, message)
        if self._answer_matches(problem, message):
            return self._handle_correct_answer(state)

        state.attempts_on_problem += 1
        self._refresh_public_state(state, include_problem=True)
        if state.attempts_on_problem == 1:
            hint = problem.get("hint") or "Use the equation on the board and substitute carefully."
            return f"Not quite.\n\nHint: {hint}\n\nTry once more."
        return self._show_solution(state)

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
            return f"Good. That is correct: {answer_text}.\n\nNow try one more.\n\n{state.active_problem['prompt']}"

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

        state.stage = "WRAP"
        state.active_problem = None
        state.attempts_on_problem = 0
        self._refresh_public_state(state, include_problem=False)
        return f"Excellent. That is correct: {answer_text}.\n\nWe have completed the guided class for {state.topic_title}. If you want, I can now revise the chapter or give mixed practice."

    def _give_hint(self, state: ClassroomState) -> str:
        if not state.active_problem:
            return "Ask me to start a practice question first."
        state.attempts_on_problem += 1
        self._refresh_public_state(state, include_problem=True)
        hint = state.active_problem.get("hint") or "Look at the board example and solve one step at a time."
        return f"Here is the teacher hint.\n\n{hint}\n\nNow try again: {state.active_problem['prompt']}"

    def _show_solution(self, state: ClassroomState) -> str:
        problem = state.active_problem
        if not problem:
            return "There is no active class question right now."

        steps = problem.get("steps") or ["Solve the equation step by step."]
        answer_text = self._format_expected_answer(problem)
        state.note_cards = list(dict.fromkeys([*state.note_cards, *steps]))[:6]
        whiteboard_lines = list(state.whiteboard.get("chalk_lines", []))
        whiteboard_lines.extend(steps[:3])
        state.whiteboard["chalk_lines"] = [line for line in dict.fromkeys(whiteboard_lines)][:5]

        response = "Let us solve it together on the board.\n\n"
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

        state.stage = "WRAP"
        state.active_problem = None
        self._refresh_public_state(state, include_problem=False)
        return "We have completed the guided class. I can revise the chapter or give mixed practice next."

    def _answer_like_teacher(self, state: ClassroomState, message: str) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        support = self._supporting_ncert_point(message)
        state.stage = "TEACH"
        self._refresh_public_state(state, include_problem=state.active_problem is not None)

        parts = ["Let us slow it down and do it like a classroom explanation."]
        if concept:
            parts.append(f"In {concept['title']}, the core idea is this: {concept.get('explanation', '')}")
            board_work = concept.get("board_work", [])
            if board_work:
                parts.append(f"On the board, keep this in mind: {board_work[0]}")
        elif topic:
            parts.append(topic.get("summary", "We will build the idea from the chapter basics."))
        if support:
            parts.append(f"NCERT support: {support}")
        if state.active_problem:
            parts.append(f"After that, come back to the class question: {state.active_problem['prompt']}")
        else:
            parts.append("If you want, I can now give you one short practice question.")
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


    def _looks_like_answer_attempt(self, state: LessonState, message: str) -> bool:
        problem = self._current_problem(state)
        if not problem:
            return False

        answer_type = problem.get("answer_type", "number")
        if answer_type == "number":
            return self.extract_number(message) is not None
        if answer_type == "pair":
            return self.extract_pair(message) is not None

        lower = message.lower().strip()
        return lower in {"yes", "no", "true", "false"} or len(lower.split()) <= 4

    def _pair_matches(self, candidate: tuple[float, float] | None, expected: list[float]) -> bool:
        if candidate is None:
    def _should_treat_as_answer(self, state: ClassroomState, lowered: str) -> bool:
        if state.active_problem is None:
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
            return [float(numbers[0]), float(numbers[1])] if len(numbers) >= 2 else None
        if answer_type == "text":
            letters = re.sub(r"[^a-z]", "", raw_message.lower())
            return letters or None
        return raw_message.strip().lower() or None

    def _answer_matches(self, problem: dict[str, Any], raw_message: str) -> bool:
        parsed = self._parse_answer(problem, raw_message)
        if parsed is None:
            return False
        answer_type = problem.get("answer_type")
        expected = problem.get("answer")
        if answer_type == "number":
            return abs(float(expected) - float(parsed)) < 1e-9
        if answer_type == "pair":
            expected_pair = [float(value) for value in expected]
            parsed_pair = [float(value) for value in parsed]
            return all(abs(a - b) < 1e-9 for a, b in zip(expected_pair, parsed_pair[:2]))
        if answer_type == "text":
            accepted = [str(expected).lower(), *[item.lower() for item in problem.get("accepted_answers", [])]]
            return str(parsed).lower() in accepted
        return str(parsed).strip().lower() == str(expected).strip().lower()

    def _format_expected_answer(self, problem: dict[str, Any]) -> str:
        answer_type = problem.get("answer_type")
        expected = problem.get("answer")
        if answer_type == "pair" and isinstance(expected, list) and len(expected) >= 2:
            return f"x = {expected[0]}, y = {expected[1]}"
        return str(expected)

    def _current_problem(self, state: ClassroomState) -> dict[str, Any] | None:
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if not concept or not concept.get("practice_problems"):
            return None
        index = min(state.current_question_index, len(concept["practice_problems"]) - 1)
        return concept["practice_problems"][index]

    def _refresh_public_state(self, state: ClassroomState, include_problem: bool) -> None:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        state.topic_title = topic["title"] if topic else state.topic_title
        state.concept_title = concept["title"] if concept else state.concept_title
        state.note_cards = self._build_note_cards(topic, concept)
        state.whiteboard = self._build_whiteboard(topic, concept, state.active_problem if include_problem else None)
        topic_title = topic["title"] if topic else "Math lesson"
        if concept and include_problem and state.active_problem:
            state.summary = f"{topic_title}: teaching {concept['title']} and waiting for the student's answer."
        elif concept:
            state.summary = f"{topic_title}: focused on {concept['title']} with a guided classroom explanation."
        else:
            state.summary = f"{topic_title}: guided classroom session is ready."

You've completed this part of **{state.topic_title}**. Next, we move to **{next_concept['title']}** so your understanding builds naturally.

{self._build_guided_explanation(state)}"""

        state.step = "REFLECTION"
        state.homework_given = True
        state.notes = [
            f"Completed guided practice in {state.topic_title}.",
            "Homework suggested for revision.",
            "Saved for future review in the class archive.",
        ]
        state.last_summary = f"Completed the guided class on {state.topic_title} with successful practice."
        return f"""Excellent work today.

**Class wrap-up**
- You completed guided practice for **{state.topic_title}**
- You can reopen this class later from your archive
- Next time we can revise, solve harder questions, or switch chapters

**Homework**
- Create one more example like today's problem
- Solve it by showing every step
- Come back and ask me to check it

Say **revise** if you want a short recap right now."""

    def process(self, session_id: str, message: str, session_record=None) -> str:
        state = self.hydrate_session(session_id, session_record)
        topic = self._ensure_topic(state)
        cleaned = message.strip()

        if not cleaned:
            if session_record and session_record.transcript:
                return self._build_resume(state, session_record)
            return self._build_intro(state, session_record)

        requested_topic = find_topic_by_message(state.grade, cleaned)
        if requested_topic and requested_topic["slug"] != state.topic_slug:
            self._switch_topic(state, requested_topic)
            return f"""Sure. We'll switch to **{requested_topic['title']}**.

**Lesson reset**
- Grade: **Class {state.grade}**
- New chapter: **{requested_topic['title']}**
- Focus: {requested_topic.get('summary', 'Guided understanding and practice')}

Say **ready** when you want me to teach this chapter."""

        if self.is_off_topic(cleaned):
            state.last_summary = f"Redirected the conversation back to mathematics for Class {state.grade}."
            return (
                f"I'm here as your mathematics tutor, so let's stay inside **CBSE Class {state.grade} Mathematics**. "
                f"We can continue with **{topic['title']}** or switch to another chapter from your syllabus."
            )

        if self.is_break(cleaned):
            state.last_summary = f"Paused the class on {topic['title']}."
            return "We can pause here. Your lesson is saved, so come back anytime and say **continue**."

        if self.is_greeting(cleaned) and state.step == "INTRO":
            return self._build_intro(state, session_record)

        if self.wants_revision(cleaned):
            state.last_summary = f"Revision requested for {topic['title']}."
            notes = "\n".join(f"- {note}" for note in state.notes[:4])
            return f"""Quick revision for **{topic['title']}**.

{notes or f'- {topic.get("summary", "We are building understanding step by step.")}'}

If you want, say **practice** for a new problem or ask a specific doubt."""

        if state.step in {"INTRO", "TOPIC_INTRODUCTION"}:
            if self.is_question(cleaned):
                state.last_summary = f"Answered an introductory doubt in {topic['title']}."
                answer = self._keyword_explanation(state, cleaned)
                return f"{answer}\n\nSay **ready** when you want the guided lesson to begin."

            if self.is_ready(cleaned) or self.wants_practice(cleaned):
                if self.wants_practice(cleaned):
                    return self._start_practice(state)
                return self._build_guided_explanation(state)

            return (
                f"We are set up for {topic['title']}. "
                "I will stay grounded to CBSE NCERT and keep a moderate pace with pauses. "
                "You can say something natural like start the lesson, explain this chapter, or ask your doubt first."
            )

        if state.step == "GUIDED_EXPLANATION":
            if self.is_question(cleaned):
                state.last_summary = f"Answered a concept question in {topic['title']}."
                return self._keyword_explanation(state, cleaned)

            if self.wants_practice(cleaned) or self.is_ready(cleaned):
                return self._start_practice(state)

            return self._start_practice(state)

        if state.step == "PRACTICE":
            lower = cleaned.lower()
            if "hint" in lower or "help" in lower or "explain" in lower or "how" in lower:
                return self._practice_help(state)
            if self._looks_like_answer_attempt(state, cleaned):
                return self._evaluate_practice(state, cleaned)
            if self.is_question(cleaned):
                return self._practice_help(state)
            return self._evaluate_practice(state, cleaned)

        if state.step == "REFLECTION":
            if self.wants_practice(cleaned):
                state.step = "PRACTICE"
                state.current_question_index = 0
                return self._start_practice(state)
            if self.is_question(cleaned):
                return self._keyword_explanation(state, cleaned)
            return (
                "Your class notes are saved. I remember what we covered. Ask for a revision, try another chapter, or simply say give me another problem."
            )

        state.last_summary = f"Continuing guided teaching in {topic['title']}."
        return (
            f"We're continuing with **{topic['title']}**. Ask a doubt, say **practice**, "
            "or ask me to switch to another chapter."
        )
    def _build_note_cards(self, topic: dict | None, concept: dict | None) -> list[str]:
        cards: list[str] = []
        if topic:
            cards.extend([topic.get("teaching_anchor", ""), topic.get("classroom_goal", ""), topic.get("summary", "")])
        if concept:
            cards.append(concept.get("explanation", ""))
            cards.extend(concept.get("board_work", [])[:2])
        return [card for card in dict.fromkeys(card.strip() for card in cards if card and card.strip())][:6]

    def _build_whiteboard(self, topic: dict | None, concept: dict | None, problem: dict[str, Any] | None) -> dict[str, Any]:
        board_work = concept.get("board_work", []) if concept else []
        equations = [line for line in board_work if "=" in line][:3]
        chalk_lines = [line for line in board_work if "=" not in line][:3]
        if concept and concept.get("explanation"):
            chalk_lines = [concept["explanation"], *chalk_lines][:4]
        whiteboard = {
            "title": topic["title"] if topic else "CBSE Mathematics",
            "subtitle": concept["title"] if concept else "Guided classroom board",
            "chalk_lines": chalk_lines,
            "equations": equations,
        }
        if problem:
            whiteboard["problem"] = problem["prompt"]
        return whiteboard

    def _retrieve_documents(self, query: str):
        if retriever is None:
            return []
        if hasattr(retriever, "invoke"):
            return retriever.invoke(query)
        if hasattr(retriever, "get_relevant_documents"):
            return retriever.get_relevant_documents(query)
        raise AttributeError("Retriever does not support invoke() or get_relevant_documents().")

    def _get_cbse_context(self, query: str) -> str:
        if retriever is None:
            init_cbse()
        if retriever is None:
            return ""
        try:
            docs = self._retrieve_documents(query) or []
            print("Retrieved docs:", len(docs))
            return "\n\n".join(doc.page_content for doc in docs if getattr(doc, "page_content", None))
        except Exception as error:
            print("Retrieval error:", error)
            return ""

    def _supporting_ncert_point(self, query: str) -> str:
        context = self._get_cbse_context(query)
        if not context:
            return ""
        flat = " ".join(context.split())
        sentences = re.split(r"(?<=[.!?])\s+", flat)
        for sentence in sentences:
            cleaned = sentence.strip()
            if 40 <= len(cleaned) <= 180:
                return cleaned
        return flat[:160].strip()
