from __future__ import annotations

import re

from ..models.session import LessonSnapshot
from ..services.ai_gateway import generate_response
from .curriculum import (
    build_curriculum_grounding,
    find_topic_by_message,
    get_concept,
    get_default_topic_slug,
    get_next_concept,
    get_topic,
    list_chapters,
)
from .lesson_state import LessonState


class TutorEngine:
    def __init__(self):
        self.sessions: dict[str, LessonState] = {}
        self.ready_keywords = ["ready", "start", "begin", "continue", "let's go", "lets go"]
        self.break_keywords = ["pause", "stop", "break", "rest"]
        self.practice_keywords = ["practice", "quiz", "problem", "exercise", "test me"]
        self.revision_keywords = ["revise", "review", "summary", "recap"]
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

        state.grade = session_record.grade
        state.step = session_record.lesson_stage or state.step
        state.topic_slug = session_record.topic_slug or get_default_topic_slug(state.grade)
        topic = get_topic(state.grade, state.topic_slug)
        if topic:
            state.topic_title = topic["title"]

        concept_id = session_record.metadata.get("concept_id") if session_record.metadata else None
        concept = get_concept(state.grade, state.topic_slug, concept_id)
        if concept:
            state.current_concept_id = concept["id"]
            state.current_concept_title = concept["title"]
            state.current_concept = concept

        notes = session_record.lesson_notes or []
        state.notes = notes[:6]
        state.last_summary = session_record.summary or state.last_summary
        if session_record.metadata:
            state.whiteboard = session_record.metadata.get("whiteboard", {}) or {}
        return state

    def _current_problem(self, state: LessonState) -> dict | None:
        concept = self._ensure_concept(state)
        if not concept:
            return None

        problems = concept.get("practice_problems", [])
        if not problems:
            return None

        index = min(state.current_question_index, len(problems) - 1)
        return problems[index]

    def _build_whiteboard(self, state: LessonState) -> dict:
        topic = self._ensure_topic(state)
        concept = self._ensure_concept(state)
        payload = {
            "title": concept["title"] if concept else topic["title"],
            "subtitle": f"Class {state.grade} • {topic['title']}",
            "chalk_lines": state.notes[:4]
            or [topic.get("summary", "We are building this idea step by step.")],
            "equations": [],
        }

        if topic["slug"] == "linear_equations_in_two_variables":
            if concept and concept["id"] == "graphing_pairs":
                payload["equations"] = ["x + y = 4", "(1, 3), (2, 2), (3, 1)"]
                payload["graph"] = {
                    "x_min": 0,
                    "x_max": 4,
                    "y_min": 0,
                    "y_max": 4,
                    "lines": [
                        {
                            "label": "x + y = 4",
                            "color": "#60a5fa",
                            "points": [[0, 4], [4, 0]],
                        }
                    ],
                    "points": [
                        {"x": 1, "y": 3, "label": "(1,3)", "color": "#f59e0b"},
                        {"x": 2, "y": 2, "label": "(2,2)", "color": "#f59e0b"},
                        {"x": 3, "y": 1, "label": "(3,1)", "color": "#f59e0b"},
                    ],
                }
            else:
                payload["equations"] = ["x + y = 7", "If x = 2, then y = 5"]

        if topic["slug"] == "pair_of_linear_equations_in_two_variables":
            if concept and concept["id"] == "graphical_meaning":
                payload["equations"] = ["x + y = 3", "x - y = 1", "Solution: (2, 1)"]
                payload["graph"] = {
                    "x_min": 0,
                    "x_max": 4,
                    "y_min": 0,
                    "y_max": 4,
                    "lines": [
                        {
                            "label": "x + y = 3",
                            "color": "#34d399",
                            "points": [[0, 3], [3, 0]],
                        },
                        {
                            "label": "x - y = 1",
                            "color": "#f97316",
                            "points": [[1, 0], [3, 2]],
                        },
                    ],
                    "points": [
                        {"x": 2, "y": 1, "label": "solution", "color": "#fef08a"}
                    ],
                }
            elif concept and concept["id"] == "substitution_and_elimination":
                payload["equations"] = [
                    "2x + y = 7",
                    "x + y = 5",
                    "Subtract => x = 2",
                    "Then y = 3",
                ]

        if state.step == "PRACTICE":
            problem = self._current_problem(state)
            if problem:
                payload["problem"] = problem["prompt"]
                payload["chalk_lines"] = [
                    f"Practice focus: {problem['prompt']}",
                    f"Hint: {problem.get('hint', 'Take it one step at a time.')}",
                ]

        state.whiteboard = payload
        return payload

    def snapshot(self, session_id: str) -> LessonSnapshot:
        state = self._state_for(session_id)
        return LessonSnapshot(
            stage=state.step,
            topic_slug=state.topic_slug,
            topic_title=state.topic_title,
            concept_id=state.current_concept_id or None,
            concept_title=state.current_concept_title or None,
            summary=state.last_summary,
            note_cards=state.notes[:6],
            whiteboard=self._build_whiteboard(state),
        )

    def is_question(self, message: str) -> bool:
        lower = message.lower().strip()
        return "?" in lower or lower.startswith(("what", "how", "why", "when", "which", "can", "does"))

    def is_ready(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.ready_keywords)

    def is_break(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.break_keywords)

    def is_greeting(self, message: str) -> bool:
        return message.lower().strip() in self.greeting_keywords

    def wants_practice(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.practice_keywords)

    def wants_revision(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.revision_keywords)

    def is_off_topic(self, message: str) -> bool:
        lower = message.lower()
        if any(keyword in lower for keyword in self.math_keywords):
            return False
        return any(
            phrase in lower
            for phrase in ["joke", "weather", "movie", "music", "sports", "politics", "your name", "who are you"]
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
        top_chapters = list_chapters(grade)[:6]
        return "\n".join(f"- {chapter['title']}" for chapter in top_chapters)

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
            f"By the end of this lesson, you should feel comfortable with {topic.get('classroom_goal', topic.get('summary', 'the main idea of this chapter'))}.\n\n"
            "We'll keep it simple. First I will explain the idea in an easy way, then we'll see it on the whiteboard, and then you will try one question with me.\n\n"
            "When you're ready, say ready. If you want to jump straight into a question, say practice."
        )

    def _build_resume(self, state: LessonState, session_record) -> str:
        topic = self._ensure_topic(state)
        state.notes = [
            f"Resumed saved class on {topic['title']}.",
            session_record.summary or f"Continue building confidence in {topic['title']}.",
        ]
        state.last_summary = session_record.summary or f"Resumed class on {topic['title']}."
        return (
            "Welcome back.\n\n"
            f"Last time we were working on {topic['title']} in Class {state.grade}. "
            f"Our last checkpoint was: {session_record.summary or 'we are ready to continue.'}\n\n"
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
                "We'll take one idea at a time and keep the pace calm.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will build the idea step by step.'))}\n\n"
                "Ask a doubt any time, or say practice when you want a question."
            )

        board_steps = concept.get("board_work", [])[:3]
        board_script = " ".join(board_steps) if board_steps else "We will solve a simple example together."
        state.notes = [
            f"Concept: {concept['title']}",
            topic.get("teaching_anchor", topic.get("summary", "")),
            "Next move: guided practice.",
        ]
        state.last_summary = f"Explaining {concept['title']} in {topic['title']}."
        return (
            f"Let's begin with {concept['title']}.\n\n"
            f"Here is the main idea in a simple way. {concept['explanation']}\n\n"
            f"{topic.get('teaching_anchor', 'We will connect the idea to classroom-style examples.')}\n\n"
            f"Now look at the whiteboard with me. {board_script}\n\n"
            "Take a moment to notice the pattern. Then ask me a doubt, or say practice and I'll give you a guided question."
        )

    def _keyword_explanation(self, state: LessonState, message: str) -> str | None:
        lower = message.lower()
        topic = self._ensure_topic(state)

        if "coefficient" in lower:
            return "A coefficient is the number multiplying a variable. In 2x + y = 7, the coefficient of x is 2."

        if "variable" in lower:
            return "A variable is a symbol whose value can change. In x + y = 7, both x and y are variables."

        if "graph" in lower or "line" in lower:
            return (
                "Each solution of a linear equation gives one point. When you plot several solutions, "
                "those points lie on a straight line."
            )

        if "substitution" in lower:
            return (
                "Substitution means first expressing one variable in terms of the other, then placing that result "
                "into the second equation."
            )

        if "elimination" in lower:
            return (
                "Elimination means adding or subtracting equations so one variable cancels out, "
                "making the system easier to solve."
            )

        if "chapter" in lower or "syllabus" in lower:
            return f"Here are common Class {state.grade} chapters we can study:\n{self._chapter_menu(state.grade)}"

        prompt = f"""
You are Ava, a warm CBSE Mathematics tutor speaking live to one student.
Answer in a natural classroom voice, not like textbook notes.
Use 2 to 3 short spoken sentences.
Keep the pace calm, warm, and simple.
Do not use bullets or headings.
After one clear explanation, ask one small check-in question if helpful.

Current grade: {state.grade}
Current chapter: {topic['title']}
Curriculum grounding:
{build_curriculum_grounding(state.grade)}

Student question:
{message}
""".strip()
        return generate_response(prompt)

    def _start_practice(self, state: LessonState) -> str:
        concept = self._ensure_concept(state)
        state.step = "PRACTICE"
        state.current_question_index = 0
        state.correct_answers_in_concept = 0

        if not concept:
            state.last_summary = f"Practice requested for {state.topic_title}."
            return "Let's do guided practice. Ask me for a sample problem from this chapter and I will create one."

        problem = concept["practice_problems"][state.current_question_index]
        state.notes = [
            f"Practice started for {concept['title']}.",
            "Student is solving a guided problem.",
        ]
        state.last_summary = f"Practice has started for {concept['title']}."
        return (
            "Practice time.\n\n"
            f"Here is your first question: {problem['prompt']}\n\n"
            "Say your answer when you're ready, or say hint if you want help."
        )

    def _practice_help(self, state: LessonState) -> str:
        concept = self._ensure_concept(state)
        if not concept:
            return "Tell me which chapter you want help with, and I will guide you from the basics."

        problem = concept["practice_problems"][state.current_question_index]
        steps = " ".join(problem.get("steps", [])[:3]) or "Start by rewriting the problem carefully."
        return (
            "Let's work it out together.\n\n"
            f"Here is a helpful hint: {problem.get('hint', 'Take it one algebra step at a time.')}\n\n"
            f"Follow this flow with me. {steps}\n\n"
            "Now you try the final answer."
        )

    def _pair_matches(self, candidate: tuple[float, float] | None, expected: list[float]) -> bool:
        if candidate is None:
            return False
        return abs(candidate[0] - expected[0]) < 0.01 and abs(candidate[1] - expected[1]) < 0.01

    def _evaluate_practice(self, state: LessonState, message: str) -> str:
        concept = self._ensure_concept(state)
        if not concept:
            return "Let's choose a chapter with practice problems first."

        problems = concept.get("practice_problems", [])
        if not problems:
            return "This concept does not have stored practice yet, but I can still teach it step by step."

        current = problems[state.current_question_index]
        answer_type = current.get("answer_type", "number")
        correct = False

        if answer_type == "number":
            number = self.extract_number(message)
            correct = number is not None and abs(number - current["answer"]) < 0.01
        elif answer_type == "pair":
            correct = self._pair_matches(self.extract_pair(message), current["answer"])
        else:
            lower = message.lower().strip()
            accepted = [current.get("answer", "")]
            accepted.extend(current.get("accepted_answers", []))
            correct = lower in {str(item).lower() for item in accepted}

        state.total_attempts += 1
        state.last_answer_correct = correct

        if not correct:
            state.last_summary = f"Student is still working on {concept['title']}."
            return (
                "Not yet, but you're close.\n\n"
                f"Here is a hint: {current.get('hint', 'Slow down and substitute carefully.')}\n\n"
                "If you want, say explain the steps and I will solve it with you."
            )

        state.correct_answers_in_concept += 1
        state.current_question_index += 1
        state.notes = [
            f"Student answered correctly in {concept['title']}.",
            f"Correct responses in this concept: {state.correct_answers_in_concept}.",
        ]

        if state.current_question_index < len(problems):
            next_problem = problems[state.current_question_index]
            state.last_summary = f"Student is progressing through practice in {concept['title']}."
            return (
                "Correct.\n\n"
                f"Let's take the next guided problem. {next_problem['prompt']}"
            )

        next_concept = get_next_concept(state.grade, state.topic_slug, state.current_concept_id)
        if next_concept:
            state.current_concept_id = next_concept["id"]
            state.current_concept_title = next_concept["title"]
            state.current_concept = next_concept
            state.current_question_index = 0
            state.correct_answers_in_concept = 0
            state.step = "GUIDED_EXPLANATION"
            state.last_summary = f"Completed practice for one concept in {state.topic_title}."
            return f"""Well done.

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
                f"We're set up for **{topic['title']}**. Say **ready** to begin the guided lesson, "
                "or ask a doubt before we start."
            )

        if state.step == "GUIDED_EXPLANATION":
            if self.is_question(cleaned):
                state.last_summary = f"Answered a concept question in {topic['title']}."
                return self._keyword_explanation(state, cleaned)

            if self.wants_practice(cleaned) or self.is_ready(cleaned):
                return self._start_practice(state)

            return self._start_practice(state)

        if state.step == "PRACTICE":
            if self.is_question(cleaned) or "hint" in cleaned.lower() or "help" in cleaned.lower():
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
                "Your class notes are saved. Ask for a revision, try another chapter, or say **practice** for more problems."
            )

        state.last_summary = f"Continuing guided teaching in {topic['title']}."
        return (
            f"We're continuing with **{topic['title']}**. Ask a doubt, say **practice**, "
            "or ask me to switch to another chapter."
        )
