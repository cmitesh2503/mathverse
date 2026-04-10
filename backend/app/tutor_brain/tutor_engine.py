from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

from .curriculum import find_topic_by_message, get_concept, get_default_topic_slug, get_next_concept, get_topic
from .lesson_state import LessonState


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
