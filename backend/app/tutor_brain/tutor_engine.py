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
from datetime import datetime, timedelta


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
            "i understand",
            "understood",
            "got it",
            "clear",
            "makes sense",
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

    def _should_take_break(self, state: LessonState) -> bool:
        if state.break_taken or not state.start_time:
            return False
        elapsed = datetime.now() - state.start_time
        return elapsed >= timedelta(minutes=30)

    def _build_break_message(self, state: LessonState) -> str:
        state.break_taken = True
        state.last_summary = f"Taking a 5-minute break in {state.topic_title} class."
        return (
            "We've been working for about 30 minutes. Let's take a 5-minute break.\n\n"
            "Stretch, get some water, and come back when you're ready.\n\n"
            "Say 'continue' or 'ready' when you want to resume the class."
        )

    def _build_analogy(self, state: LessonState) -> str:
        topic = self._ensure_topic(state)
        concept = self._ensure_concept(state)

        if concept:
            if topic["slug"] == "linear_equations_in_two_variables":
                if concept["id"] == "form_and_solution":
                    return "It is like choosing two numbers that keep a balance true; only the right pair of x and y makes the equation work."
                if concept["id"] == "graphing_pairs":
                    return "It is like plotting points on a map. Each solution is a point, and all the points together make a straight road."
            if topic["slug"] == "pair_of_linear_equations_in_two_variables":
                if concept["id"] == "graphical_meaning":
                    return "It is like two roads meeting at one crossing point. That crossing is the solution that satisfies both equations."
                if concept["id"] == "substitution_and_elimination":
                    return "It is like using one equation to find one number first, then placing it into the other equation, or removing the same amount from both sides to simplify."

        if topic["slug"] == "linear_equations_in_two_variables":
            return "Think of it like a straight road on a map: each point that lies on the road is a solution to the equation."
        if topic["slug"] == "pair_of_linear_equations_in_two_variables":
            return "Imagine two lines on the same page. Their crossing point is the solution that works for both."
        return "Think of this idea like a simple rule you can use again and again; once it clicks, you can solve similar problems with confidence."

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
            f"Hi {student_label}. I'm Ava, and today we'll start Chapter {topic['title']} for Class {state.grade}.\n\n"
            f"In this lesson, we'll learn {topic.get('classroom_goal', topic.get('summary', 'the main idea of this chapter'))}.\n\n"
            "I'll explain the first idea clearly with a simple analogy, then ask if it makes sense before we move on."
        )
        lesson_start = self._build_guided_explanation(state)
        state.last_summary = f"Started a guided class on {topic['title']}."
        if not state.start_time:
            state.start_time = datetime.now()
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
        state.step = "CONFIRM_UNDERSTANDING"

        if not concept:
            analogy = self._build_analogy(state)
            state.notes = [
                f"Discussing {topic['title']}",
                topic.get("summary", "Concept discussion in progress."),
            ]
            state.last_summary = f"Guided explanation in progress for {topic['title']}."
            return (
                f"Let's start with {topic['title']}.\n\n"
                "We'll take one idea at a time and keep the pace calm.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will build the idea step by step.'))}\n\n"
                f"A helpful way to think about it is: {analogy}\n\n"
                "Does that make sense so far? If you want, I can explain it again or show one example."
            )

        board_steps = concept.get("board_work", [])[:3]
        board_script = " ".join(board_steps) if board_steps else "We will solve a simple example together."
        analogy = self._build_analogy(state)
        state.notes = [
            f"Concept: {concept['title']}",
            topic.get("teaching_anchor", topic.get("summary", "")),
            "Next move: guided practice.",
        ]
        state.last_summary = f"Explaining {concept['title']} in {topic['title']}."
        return (
            f"Let's begin with {concept['title']}.\n\n"
            f"Here is the main idea in a simple way. {concept['explanation']}\n\n"
            f"A helpful analogy is: {analogy}\n\n"
            f"{topic.get('teaching_anchor', 'We will connect the idea to classroom-style examples.')}\n\n"
            f"Now look at the whiteboard with me. {board_script}\n\n"
            "Take a moment to notice the pattern. Do you understand this so far? I can explain it again in a simpler way or give you one more example."
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
        state.step = "CONFIRM_UNDERSTANDING"

        if not concept:
            analogy = self._build_analogy(state)
            state.last_summary = f"Re-explained the main idea in {topic['title']}."
            return (
                f"No problem. Let's slow it down.\n\n"
                f"{topic.get('teaching_anchor', topic.get('summary', 'We will build the idea step by step.'))}\n\n"
                f"A helpful way to remember it is: {analogy}\n\n"
                "I'll keep it simple. After this, I can show one example."
            )

        board_work = concept.get("board_work", [])
        simple_example = board_work[0] if board_work else "We will use one small example and build from there."
        analogy = self._build_analogy(state)
        state.notes = [
            f"Re-explaining {concept['title']} slowly.",
            simple_example,
            "Student asked for a simpler explanation.",
        ]
        state.last_summary = f"Re-explained {concept['title']} more slowly."
        return (
            f"No problem. Let's take {concept['title']} one step at a time.\n\n"
            f"The key idea is this: {concept['explanation']}\n\n"
            f"A helpful analogy is: {analogy}\n\n"
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
        
        # Check if it looks like a pair answer (contains comma with numbers)
        if "," in message:
            pair = self.extract_pair(message)
            if pair is not None:
                return True

        if answer_type == "number":
            # Don't match if it's clearly a pair (has comma)
            if "," not in message:
                return self.extract_number(message) is not None
            return False
        if answer_type == "pair":
            return self.extract_pair(message) is not None

        # For text answers
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

        # Limit to 3 problems
        problems = concept.get("practice_problems", [])[:3]

        problem = problems[state.current_question_index]
        state.notes = [
            f"Practice started for {concept['title']}.",
            "Student is solving guided problems (3-5 total).",
        ]
        state.last_summary = f"Practice has started for {concept['title']}."
        
        # Add expected answer format
        format_hint = ""
        if problem.get("answer_type") == "number":
            format_hint = " (Give your answer as a number, like '5' or '2.5')"
        elif problem.get("answer_type") == "pair":
            format_hint = " (Give your answer as two numbers separated by a comma, like '2, 3')"
        else:
            format_hint = " (Give your answer clearly)"
        
        return (
            "Practice time.\n\n"
            f"Here is your first question: {problem['prompt']}{format_hint}\n\n"
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
        # Limit to 3-5 problems
        if len(problems) > 5:
            problems = problems[:5]
        elif len(problems) < 3:
            problems = problems  # Use all if less than 3

        if not problems:
            return "This concept does not have stored practice yet, but I can still teach it step by step."

        current = problems[state.current_question_index]
        answer_type = current.get("answer_type", "number")
        correct = False
        
        # Try to deduce answer_type from the expected answer if not set
        if not answer_type or answer_type == "number":
            expected_answer = current.get("answer")
            if isinstance(expected_answer, (list, tuple)) and len(expected_answer) == 2:
                answer_type = "pair"

        if answer_type == "pair":
            # Check if message looks like a pair
            if "," in message or self.extract_pair(message) is not None:
                correct = self._pair_matches(self.extract_pair(message), current["answer"])
            else:
                # Try to extract two numbers anyway
                nums = self._numbers_in_text(message)
                if len(nums) >= 2:
                    correct = self._pair_matches((nums[0], nums[1]), current["answer"])
        elif answer_type == "number":
            number = self.extract_number(message)
            if number is not None and isinstance(current["answer"], (int, float)):
                correct = abs(number - current["answer"]) < 0.01
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
            state.last_summary = f"Student needs help with {concept['title']}."
            # Show solution on whiteboard and explain
            steps = " ".join(current.get("steps", [])[:4]) or f"The solution is {current.get('answer', 'shown above')}."
            explanation = current.get("explanation", "Let's work through this together.")
            state.notes = [
                f"Student answered incorrectly for {concept['title']}.",
                f"Correct answer: {current.get('answer', 'see whiteboard')}",
                steps,
            ]
            # Move to next question after showing solution
            state.current_question_index += 1
            if state.current_question_index < len(problems):
                next_problem = problems[state.current_question_index]
                # Add format hint for next problem
                format_hint = ""
                next_answer_type = next_problem.get("answer_type", "number")
                if isinstance(next_problem.get("answer"), (list, tuple)) or next_answer_type == "pair":
                    format_hint = " (Answer as two numbers with comma: like '2, 1')"
                elif next_answer_type == "number":
                    format_hint = " (Give a number)"
                return (
                    f"Not quite right. Let me show you: {steps}\n\n"
                    f"{explanation}\n\n"
                    f"Now try this: {next_problem['prompt']}{format_hint}"
                )
            else:
                # End practice if no more questions
                state.step = "REFLECTION"
                state.homework_given = True
                return (
                    f"Not quite right. Here's the correct way: {steps}\n\n"
                    f"{explanation}\n\n"
                    "That's all the practice for now. Great effort!"
                )

        state.correct_answers_in_concept += 1
        state.current_question_index += 1
        state.notes = [
            f"Student answered correctly in {concept['title']}.",
            f"Correct responses in this concept: {state.correct_answers_in_concept}.",
        ]

        # Limit to 3-5 problems: after 3 correct answers, move to reflection
        if state.correct_answers_in_concept >= 3:
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

        if state.current_question_index < len(problems):
            next_problem = problems[state.current_question_index]
            state.last_summary = f"Student is progressing through practice in {concept['title']}."
            return (
                "Correct! Well done.\n\n"
                f"Next question: {next_problem['prompt']}"
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

        # Check for break time
        if self._should_take_break(state):
            return self._build_break_message(state)

        if not cleaned and state.step == "INTRO":
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

        # Handle break resumption
        if state.break_taken and (self.is_ready(cleaned) or self.is_affirmative(cleaned) or "continue" in cleaned.lower()):
            state.last_summary = f"Resumed class on {topic['title']} after break."
            return f"Welcome back. Let's continue with {topic['title']}.\n\n{self._build_guided_explanation(state) if state.step == 'GUIDED_EXPLANATION' else 'What would you like to do next?'}"

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

        if state.step == "CONFIRM_UNDERSTANDING":
            if self.is_affirmative(cleaned):
                return self._build_worked_example(state)

            if self.feels_confused(cleaned):
                return self._build_reteach_support(state)

            if self.is_question(cleaned):
                state.last_summary = f"Answered a question during understanding check in {topic['title']}."
                return self._keyword_explanation(state, cleaned)

            if self.wants_example(cleaned):
                return self._build_worked_example(state)

            return "Do you understand this concept? Say 'yes' if you're ready to move on, or tell me if you need it explained again."

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
