from .lesson_state import LessonState
from .curriculum import get_topic, get_concept, get_next_concept
import re

class TutorEngine:
    def __init__(self):
        self.sessions = {}
        self.doubt_keywords = ["don't understand", "dont understand", "confused", "doubt", "why", "how"]
        self.break_keywords = ["pause", "stop", "break", "rest"]
        self.ready_keywords = ["ready", "yes", "start", "begin", "ok", "okay"]
        self.greeting_keywords = ["hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"]

    def is_doubt(self, message: str) -> bool:
        lower = message.lower()
        return any(k in lower for k in self.doubt_keywords)

    def is_break(self, message: str) -> bool:
        lower = message.lower()
        return any(k in lower for k in self.break_keywords)

    def is_ready(self, message: str) -> bool:
        lower = message.lower().strip()
        return any(k in lower for k in self.ready_keywords)

    def is_greeting(self, message: str) -> bool:
        lower = message.lower().strip()
        return lower in self.greeting_keywords

    def extract_number(self, message: str):
        """Extract number from user message"""
        numbers = re.findall(r'-?\d+\.?\d*', message)
        if numbers:
            return float(numbers[0])
        return None

    def process(self, session_id, message):
        print("TutorEngine called")

        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()

        state = self.sessions[session_id]
        print(f"STATE: {state.step}, CONCEPT: {state.current_concept_id}")

        # Auto-start lesson when connection opens (empty message)
        if not message.strip():
            if state.step == "INTRO":
                state.step = "TOPIC_INTRODUCTION"
                response = """Hello everyone! Welcome to today's Math class!

I'm **Ava**, your Math Teacher. Today we're going to learn about **Linear Equations** - one of the most important topics in mathematics.

Linear equations help us solve real-world problems like:
- How much money will you have after saving $50 each week?
- If a train travels at 60 km/h, how long will it take to go 300 km?
- What temperature is 32 degrees F in Celsius?

These equations have the form: **ax + b = c**

Where:
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

Let me explain this step by step, just like in a real classroom!"""
                return response

        # Handle greeting - acknowledge but don't interrupt current lesson
        if self.is_greeting(message):
            if state.step == "INTRO":
                # First greeting - start the teaching flow
                state.step = "TOPIC_INTRODUCTION"
                response = """Hello everyone! Welcome to today's Math class!

I'm **Ava**, your Math Teacher. Today we're going to learn about **Linear Equations** - one of the most important topics in mathematics.

Linear equations help us solve real-world problems like:
- How much money will you have after saving $50 each week?
- If a train travels at 60 km/h, how long will it take to go 300 km?
- What temperature is 32 degrees F in Celsius?

These equations have the form: **ax + b = c**

Where:
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

Let me explain this step by step, just like in a real classroom!"""
                return response
            else:
                # During lesson - acknowledge and continue
                return "Hello! I'm here to help you learn. What would you like to know about linear equations?"

        # Handle questions and doubts at any time during the lesson
        if self.is_doubt(message) or "?" in message or message.lower().startswith(("what", "how", "why", "explain", "tell me")):
            if state.current_concept:
                return f"""I understand your question! Let me explain **{state.current_concept['name']}** again.

**{state.current_concept['name']}:**
{state.current_concept['description']}

**Example:**
{state.current_concept['example_problem']}

**Solution Steps:**
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(state.current_concept['steps']))}

Does this help? You can ask me anything about linear equations!"""
            else:
                return """Great question! I'm here to help you understand linear equations.

A **linear equation** is an equation that makes a straight line when graphed. The general form is **ax + b = c**, where:
- **a** is the coefficient of x
- **x** is the variable we're solving for
- **b** and **c** are constants

Ask me anything specific about linear equations and I'll explain it!"""

        # Handle interruptions and clarifications
        if self.is_break(message):
            return "Sure, let's take a short break. Type 'ready' or 'continue' when you're prepared to learn again."

        # STEP 1: INTRO - Greet and introduce the topic
        if state.step == "INTRO":
            state.step = "TOPIC_INTRODUCTION"
            response = """Hello everyone! Welcome to today's Math class!

I'm **Ava**, your Math Teacher. Today we're going to learn about **Linear Equations** - one of the most important topics in mathematics.

Linear equations help us solve real-world problems like:
- How much money will you have after saving $50 each week?
- If a train travels at 60 km/h, how long will it take to go 300 km?
- What temperature is 32 degrees F in Celsius?

These equations have the form: **ax + b = c**

Where:
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

Let me explain this step by step, just like in a real classroom!"""
            return response

        # STEP 2: TOPIC INTRODUCTION - Explain the concept
        elif state.step == "TOPIC_INTRODUCTION":
            if self.is_ready(message):
                state.step = "CONCEPT_EXPLANATION"
                response = """Perfect! Let's dive into **Linear Equations**.

**What is a Linear Equation?**

A linear equation is an equation that makes a straight line when graphed. The standard form is:

**ax + b = c**

Where:
- **a** = coefficient (number multiplying x)
- **x** = variable (what we're solving for)
- **b** = constant term
- **c** = another constant

**Example 1: Simple Equation**
**x + 5 = 12**

To solve:
1. Subtract 5 from both sides: x + 5 - 5 = 12 - 5
2. **x = 7**

**Example 2: With multiplication**
**2x + 3 = 11**

To solve:
1. Subtract 3 from both sides: 2x + 3 - 3 = 11 - 3
2. **2x = 8**
3. Divide both sides by 2: (2x)/2 = 8/2
4. **x = 4**

**Example 3: Variables on both sides**
**3x + 2 = x + 8**

To solve:
1. Subtract x from both sides: 3x + 2 - x = x + 8 - x
2. **2x + 2 = 8**
3. Subtract 2 from both sides: 2x + 2 - 2 = 8 - 2
4. **2x = 6**
5. Divide both sides by 2: (2x)/2 = 6/2
6. **x = 3**

Ready to practice? Type "practice" to start solving problems!"""
                return response
            else:
                return "Let me know when you're ready to dive into the concepts! Just type 'ready' or 'start'."

        # STEP 3: CONCEPT EXPLANATION - Walk through concepts
        elif state.step == "CONCEPT_EXPLANATION":
            if "practice" in message.lower():
                state.step = "PRACTICE"
                state.current_concept = get_concept(state.current_concept_id or 1)
                return f"""Great! Let's practice **{state.current_concept['name']}**.

**Problem:** {state.current_concept['practice_problems'][0]['problem']}

Show your work and give me your answer!"""
            else:
                return "Type 'practice' when you're ready to solve some problems!"

        # STEP 4: PRACTICE - Give problems and check answers
        elif state.step == "PRACTICE":
            if not state.current_concept:
                state.current_concept = get_concept(1)

            current_problem = state.current_concept['practice_problems'][state.question_index]
            expected_answer = current_problem['answer']

            # Extract number from user message
            user_answer = self.extract_number(message)

            if user_answer is not None:
                if abs(user_answer - expected_answer) < 0.01:  # Allow small floating point differences
                    state.correct_answers_in_concept += 1
                    state.question_index += 1

                    # Check if concept is mastered
                    if state.correct_answers_in_concept >= state.mastery_threshold:
                        next_concept = get_next_concept(state.current_concept_id)
                        if next_concept:
                            state.current_concept_id = next_concept['id']
                            state.current_concept = next_concept
                            state.correct_answers_in_concept = 0
                            state.question_index = 0
                            state.step = "CONCEPT_EXPLANATION"
                            return f"""Excellent work! You've mastered **{state.current_concept['name']}**!

Ready to move to the next concept? Type "next" to continue!"""
                        else:
                            return """Congratulations! You've completed all the linear equation concepts!

You now understand:
- Simple linear equations (x + b = c)
- Equations with multiplication (ax + b = c)
- Equations with variables on both sides (ax + b = cx + d)

Keep practicing and you'll be a linear equations expert!"""
                    else:
                        # More problems in current concept
                        if state.question_index < len(state.current_concept['practice_problems']):
                            next_problem = state.current_concept['practice_problems'][state.question_index]
                            return f"""Correct! Great job!

**Next Problem:** {next_problem['problem']}

What's your answer?"""
                        else:
                            # Reset for more practice
                            state.question_index = 0
                            next_problem = state.current_concept['practice_problems'][0]
                            return f"""Good work! Let's practice more.

**Problem:** {next_problem['problem']}

What's your answer?"""
                else:
                    # Wrong answer
                    attempts = state.attempts_for_current_question + 1
                    state.attempts_for_current_question = attempts

                    if attempts >= 3:
                        # Give hint/solution
                        state.question_index += 1
                        state.attempts_for_current_question = 0
                        return f"""Let me help you with this one.

**Problem:** {current_problem['problem']}
**Solution:** {current_problem['solution']}

**Answer:** {expected_answer}

Let's try the next problem!"""
                    else:
                        return f"""Not quite. Try again!

**Problem:** {current_problem['problem']}

**Hint:** {current_problem['hints'][attempts-1] if attempts-1 < len(current_problem['hints']) else 'Think about the operations you need to isolate x.'}

What's your answer? (Attempt {attempts}/3)"""
            else:
                return f"""I need a number for your answer!

**Problem:** {current_problem['problem']}

Please give me a numerical answer."""

        return "I'm here to help you learn linear equations! What would you like to know?"