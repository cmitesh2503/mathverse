from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

from .curriculum import (
    find_topic_by_message,
    get_chapter_position,
    get_concept,
    get_default_topic_slug,
    get_next_concept,
    get_next_topic,
    get_topic,
)
from .lesson_state import LessonState


retriever = None
retriever_lock = Lock()
CLASS_DURATION_MINUTES = 45


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
    homework: list[str] = field(default_factory=list)
    class_duration_minutes: int = CLASS_DURATION_MINUTES
    chapter_label: str = ""


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
            if isinstance(metadata.get("homework"), list):
                state.homework = [str(item) for item in metadata["homework"][:3]]
            if getattr(session, "lesson_notes", None):
                state.note_cards = list(session.lesson_notes[:6])
            if getattr(session, "summary", None):
                state.summary = session.summary
            state.chapter_label = self._chapter_label(state.grade, state.topic_slug)
            state.active_problem = self._current_problem(state) if state.stage == "PRACTICE" else None
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

        if state.stage == "PRACTICE" and state.active_problem and any(token in lowered for token in ["hint", "clue"]):
            return self._give_hint(state)
        if state.stage == "PRACTICE" and state.active_problem and any(token in lowered for token in ["solution", "steps", "solve it", "show answer"]):
            return self._show_solution(state)
        if any(token in lowered for token in ["practice", "quiz", "test me", "ask me a question"]):
            return self._offer_practice(state)
        if any(token in lowered for token in ["homework", "assignment", "classwork"]):
            return self._give_homework(state)
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
            chapter_label=self._chapter_label(grade, topic["slug"] if topic else topic_slug),
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
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        self._refresh_public_state(state, include_problem=False)
        chapter = topic["title"] if topic else state.topic_title or "the current chapter"
        first_concept = concept["title"] if concept else "the basics"
        return (
            f"Welcome back.\n\n"
            f"Chapter: **{chapter}**\n"
            f"Topic: **{first_concept}**\n\n"
            f"We will begin with the main idea, solve the NCERT textbook examples, then solve exercise questions on the whiteboard, and keep the remaining work in the Homework tab.\n\n"
            "Say **ready** when you want me to begin."
        )

    def _build_topic_switch_response(self, state: ClassroomState) -> str:
        return (
            f"Sure.\n\n"
            f"Chapter: **{state.topic_title}**\n"
            f"Topic: **{state.concept_title or 'First topic'}**\n\n"
            "We will take the topic in order, solve the textbook examples first, then exercise problems on the whiteboard, and save the remaining homework for later revision.\n\n"
            "Say ready when you want me to begin."
        )

    def _teach_current_concept(self, state: ClassroomState, transition: bool) -> str:
        topic = get_topic(state.grade, state.topic_slug or get_default_topic_slug(state.grade))
        concept = get_concept(state.grade, state.topic_slug or get_default_topic_slug(state.grade), state.concept_id)
        if not topic or not concept:
            state.summary = "The class is ready, but the chapter selection needs to be clarified."
            return "Tell me the chapter name you want to study, and I will teach it from the basics."

        textbook_examples, exercise_problems = self._concept_problem_sets(concept)

        state.concept_id = concept["id"]
        state.concept_title = concept["title"]
        state.current_question_index = 0
        state.active_problem = None
        state.attempts_on_problem = 0
        state.stage = "TEACH"
        self._refresh_public_state(state, include_problem=False)

        board_work = concept.get("board_work", [])
        importance_note = self._important_memory_note(topic, concept)
        parts = []
        if transition:
            parts.append("Next topic.")
        parts.append(f"Chapter: **{topic['title']}**")
        parts.append(f"Topic: **{concept['title']}**")
        parts.append(concept.get("explanation", topic.get("summary", "")))
        if importance_note:
            parts.append(importance_note)
        if board_work:
            parts.append(f"On the whiteboard, I am writing: {board_work[0]}")
            if len(board_work) > 1:
                parts.append(f"Then we note: {board_work[1]}")
        if textbook_examples:
            parts.append("Let us solve the NCERT textbook examples for this topic.")
            self._append_problem_walkthrough(
                state=state,
                topic=topic,
                concept=concept,
                label="NCERT textbook example",
                problems=textbook_examples,
                parts=parts,
            )
        if exercise_problems:
            parts.append("Now let us solve a few NCERT exercise questions on the whiteboard.")
            self._append_problem_walkthrough(
                state=state,
                topic=topic,
                concept=concept,
                label="NCERT exercise problem",
                problems=exercise_problems,
                parts=parts,
            )

        if state.homework:
            parts.append("I have saved the remaining questions in the Homework tab.")
        parts.append("Say **next** when you are ready for the next topic.")
        return "\n\n".join(part for part in parts if part)

    def _offer_practice(self, state: ClassroomState) -> str:
        if state.active_problem is None:
            return (
                "I have already explained this topic and solved the textbook and exercise questions on the board.\n\n"
                "Read the whiteboard, copy the steps, and say **next** when you are ready for the next topic.\n\n"
                "You can also ask for **homework** any time."
            )
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
        parts.append("Give only the answer first. If you want, you can also ask for a hint or a full board solution.")
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
        hint = state.active_problem.get("hint") or "Look at the board example and solve one step at a time."
        return f"Important hint: {hint}\n\nNow try again: {state.active_problem['prompt']}"

    def _give_homework(self, state: ClassroomState) -> str:
        if not state.homework:
            self._refresh_public_state(state, include_problem=state.active_problem is not None)
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
        support = self._supporting_ncert_point(message)
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
            labels = problem.get("answer_labels")
            if (
                isinstance(labels, list)
                and len(labels) >= 2
                and all(isinstance(label, str) and label.strip() for label in labels[:2])
            ):
                first_label, second_label = labels[:2]
            else:
                first_label, second_label = ("x", "y")
            return f"{first_label} = {expected[0]}, {second_label} = {expected[1]}"
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
        flat = re.sub(r"Reprint\s+\d{4}-\d{2}", "", flat, flags=re.IGNORECASE)
        flat = re.sub(r"\b[A-Z][A-Z\s]{8,}\s+\d+\b", "", flat)
        flat = re.sub(r"\s+", " ", flat).strip()
        sentences = re.split(r"(?<=[.!?])\s+", flat)
        for sentence in sentences:
            cleaned = sentence.strip()
            if 40 <= len(cleaned) <= 180:
                return cleaned
        return flat[:160].strip()
