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
        self.affirmative_keywords = [
            "yes",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "go ahead",
            "go on",
            "carry on",
            "please continue",
            "continue please",
            "let's continue",
            "lets continue",
            "proceed",
            "alright",
            "all right",
        ]
        self.teaching_keywords = [
            "teach me",
            "explain",
            "start teaching",
            "teach this",
            "start the lesson",
            "continue the lesson",
            "from the basics",
        ]
        self.confusion_keywords = [
            "don't understand",
            "dont understand",
            "do not understand",
            "didn't understand",
            "didnt understand",
            "not clear",
            "confused",
            "i am confused",
            "i'm confused",
            "i do not understand",
            "explain again",
            "say again",
            "repeat",
            "once more",
            "slow down",
            "slower",
            "too fast",
            "not getting",
            "i don't get it",
            "i dont get it",
        ]
        self.example_keywords = [
            "example",
            "another example",
            "one more example",
            "show me one",
            "solve one",
            "worked example",
        ]
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

    def is_affirmative(self, message: str) -> bool:
        lower = message.lower().strip()
        return any(keyword == lower or keyword in lower for keyword in self.affirmative_keywords)

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

    def wants_teaching(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.teaching_keywords)

    def feels_confused(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.confusion_keywords)

    def wants_example(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in self.example_keywords)

    def is_off_topic(self, message: str) -> bool:
        lower = message.lower()
        if any(keyword in lower for keyword in self.math_keywords):
            return False
        return any(
            phrase in lower
            for phrase in ["joke", "weather", "movie", "music", "sports", "politics", "your name", "who are you"]
        )

    def _numbers_in_text(self, message: str) -> list[float]:
        digits = re.findall(r"-?\d+\.?\d*", message)
        if digits:
            return [float(num) for num in digits]

        word_map = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
        }
        words = re.findall(r"[a-z]+", message.lower())
        return [float(word_map[w]) for w in words if w in word_map]

    def extract_number(self, message: str) -> float | None:
        nums = self._numbers_in_text(message)
        return nums[0] if nums else None

    def extract_pair(self, message: str) -> tuple[float, float] | None:
        nums = self._numbers_in_text(message)
        if len(nums) < 2:
            return None
        return nums[0], nums[1]

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
        student_label = "Dhrumil"
        if session_record and session_record.student_id:
            student_label = (
                "Dhrumil"
                if session_record.student_id.startswith("student-")
                else session_record.student_id.replace("-", " ")
            )

        opening = (
            f"Hi {student_label}. I'm Ava, and today we'll work on {topic['title']} for Class {state.grade}.\n\n"
            f"By the end of this lesson, you should feel comfortable with {topic.get('classroom_goal', topic.get('summary', 'the main idea of this chapter'))}.\n\n"
            "I'll start teaching right away, and you can interrupt me any time if you want a doubt cleared, one more example, or a question."
        )
        lesson_start = self._build_guided_explanation(state)
        state.last_summary = f"Started a guided class on {topic['title']}."
        return f"{opening}\n\n{lesson_start}"

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
                "Ask a doubt any time, or tell me when you want a question."
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
            "Take a moment to notice the pattern. If you want, I can show one worked example next, or we can try a guided question together."
        )

    def _build_worked_example(self, state: LessonState) -> str:
        topic = self._ensure_topic(state)
        concept = self._ensure_concept(state)
        state.step = "WORKED_EXAMPLE"

        if not concept:
            state.last_summary = f"Worked example requested for {topic['title']}."
            return (
                f"Let's do one simple example from {topic['title']}.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will solve it step by step.'))}\n\n"
                "After that, I will let you try one."
            )

        board_work = concept.get("board_work", [])
        example_flow = " ".join(board_work[:3]) if board_work else concept["explanation"]
        practice = concept.get("practice_problems", [])
        prompt = practice[0]["prompt"] if practice else "We will use the same idea in a simple question."
        state.notes = [
            f"Worked example for {concept['title']}.",
            example_flow,
            f"Next student task: {prompt}",
        ]
        state.last_summary = f"Worked example shown for {concept['title']} in {topic['title']}."
        return (
            f"Let's do one worked example for {concept['title']}.\n\n"
            f"Watch this carefully. {example_flow}\n\n"
            f"Now you have seen the pattern. Next, I can give you a similar guided question: {prompt}"
        )

    def _build_reteach_support(self, state: LessonState) -> str:
        topic = self._ensure_topic(state)
        concept = self._ensure_concept(state)
        state.step = "GUIDED_EXPLANATION"

        if not concept:
            state.last_summary = f"Re-explained the main idea in {topic['title']}."
            return (
                f"No problem. Let's slow it down.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will build the idea step by step.'))}\n\n"
                "I'll keep it simple. After this, I can show one example."
            )

        board_work = concept.get("board_work", [])
        simple_example = board_work[0] if board_work else "We will use one small example and build from there."
        state.notes = [
            f"Re-explaining {concept['title']} slowly.",
            simple_example,
            "Student asked for a simpler explanation.",
        ]
        state.last_summary = f"Re-explained {concept['title']} more slowly."
        return (
            f"No problem. Let's take {concept['title']} one step at a time.\n\n"
            f"The key idea is this: {concept['explanation']}\n\n"
            f"Keep this one example in mind: {simple_example}\n\n"
            "Tell me if you want one more example, or I can give you a guided question."
        )

    def _repeat_practice_prompt(self, state: LessonState) -> str:
        problem = self._current_problem(state)
        if not problem:
            return "Tell me when you are ready, and I will give you a guided problem."

        return (
            f"Take your time. Here is the question again: {problem['prompt']}\n\n"
            "You can answer directly, or ask me for a hint."
        )

    def _is_attempt_response(self, state: LessonState, message: str) -> bool:
        problem = self._current_problem(state)
        if not problem:
            return False

        answer_type = problem.get("answer_type", "number")
        lower = message.lower().strip()

        if answer_type == "number":
            return self.extract_number(message) is not None
        if answer_type == "pair":
            return self.extract_pair(message) is not None

        accepted = [str(problem.get("answer", "")).lower()]
        accepted.extend(str(item).lower() for item in problem.get("accepted_answers", []))
        return lower in set(accepted) or any(value and value in lower for value in accepted)

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
            "Answer in your own words when you're ready, or ask for a hint if you want help."
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
            "Now you try the final answer in your own words."
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
            accepted_values = {str(item).lower() for item in accepted}
            correct = lower in accepted_values or any(
                value and value in lower for value in accepted_values
            )

        state.total_attempts += 1
        state.last_answer_correct = correct

        if not correct:
            state.last_summary = f"Student is still working on {concept['title']}."
            return (
                "Not yet, but you're close.\n\n"
                f"Here is a hint: {current.get('hint', 'Slow down and substitute carefully.')}\n\n"
                "If you want, ask me to explain the steps and I will solve it with you."
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
            return (
                f"Sure. We'll switch to {requested_topic['title']} for Class {state.grade}.\n\n"
                f"Our new focus is {requested_topic.get('summary', 'guided understanding and practice')}.\n\n"
                "I can start teaching this now, or you can ask a doubt first."
            )

        if self.is_off_topic(cleaned):
            state.last_summary = f"Redirected the conversation back to mathematics for Class {state.grade}."
            return (
                f"I'm here as your mathematics tutor, so let's stay inside **CBSE Class {state.grade} Mathematics**. "
                f"We can continue with **{topic['title']}** or switch to another chapter from your syllabus."
            )

        if self.is_break(cleaned):
            state.last_summary = f"Paused the class on {topic['title']}."
            return "We can pause here. Your lesson is saved, so come back anytime and tell me to continue."

        if self.is_greeting(cleaned) and state.step == "INTRO":
            return self._build_intro(state, session_record)

        if self.wants_revision(cleaned):
            state.last_summary = f"Revision requested for {topic['title']}."
            notes = "\n".join(f"- {note}" for note in state.notes[:4])
            return f"""Quick revision for **{topic['title']}**.

{notes or f'- {topic.get("summary", "We are building understanding step by step.")}'}

If you want, I can give you a new problem or answer a specific doubt."""

        if state.step in {"INTRO", "TOPIC_INTRODUCTION"}:
            if self.wants_practice(cleaned):
                return self._start_practice(state)

            if self.is_affirmative(cleaned) or self.is_ready(cleaned) or self.wants_teaching(cleaned):
                return self._build_guided_explanation(state)

            if self.is_question(cleaned):
                state.last_summary = f"Answered an introductory doubt in {topic['title']}."
                answer = self._keyword_explanation(state, cleaned)
                return f"{answer}\n\nIf you want, I can start the guided lesson now."

            return self._build_guided_explanation(state)

        if state.step == "GUIDED_EXPLANATION":
            if self.feels_confused(cleaned):
                return self._build_reteach_support(state)

            if self.wants_example(cleaned):
                return self._build_worked_example(state)

            if self.is_question(cleaned):
                state.last_summary = f"Answered a concept question in {topic['title']}."
                return self._keyword_explanation(state, cleaned)

            if self.wants_practice(cleaned) or self.is_ready(cleaned):
                return self._start_practice(state)

            if self.is_affirmative(cleaned) or self.wants_teaching(cleaned):
                return self._build_worked_example(state)

            return self._build_worked_example(state)

        if state.step == "WORKED_EXAMPLE":
            if self.feels_confused(cleaned):
                return self._build_reteach_support(state)

            if self.is_question(cleaned):
                return self._keyword_explanation(state, cleaned)

            if self.wants_example(cleaned):
                return self._build_worked_example(state)

            if self.wants_practice(cleaned) or self.is_affirmative(cleaned) or self.is_ready(cleaned):
                return self._start_practice(state)

            return self._start_practice(state)

        if state.step == "PRACTICE":
            if self.feels_confused(cleaned) or self.wants_example(cleaned):
                return self._practice_help(state)

            if self.is_question(cleaned) or "hint" in cleaned.lower() or "help" in cleaned.lower():
                return self._practice_help(state)

            if self.is_affirmative(cleaned) and not self._is_attempt_response(state, cleaned):
                return self._repeat_practice_prompt(state)

            if not self._is_attempt_response(state, cleaned):
                return self._repeat_practice_prompt(state)

            return self._evaluate_practice(state, cleaned)

        if state.step == "REFLECTION":
            if self.wants_practice(cleaned):
                state.step = "PRACTICE"
                state.current_question_index = 0
                return self._start_practice(state)
            if self.is_affirmative(cleaned) or self.wants_teaching(cleaned):
                return self._build_guided_explanation(state)
            if self.is_question(cleaned):
                return self._keyword_explanation(state, cleaned)
            return (
                "Your class notes are saved. Ask for a revision, try another chapter, or ask for more problems."
            )

        state.last_summary = f"Continuing guided teaching in {topic['title']}."
        return (
            f"We're continuing with {topic['title']}. Ask a doubt, ask for a question, "
            "or ask me to switch to another chapter."
        )
