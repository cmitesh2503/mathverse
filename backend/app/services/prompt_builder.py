from flask import session
from sentence_transformers import evaluation

from app.api.routes import evaluation
from app.services.teaching_strategy import TeachingStrategy


class PromptBuilder:

    def build(
        self,
        strategy,
        reasoning,
        context,
        session,
        student_message
    ):
        
        conversation = context.get(
            "conversation",
            ""
        )

        if strategy == TeachingStrategy.EXPLAIN:

            return self._normal_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        if strategy == TeachingStrategy.SIMPLIFY:

            return self._simplify_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        if strategy == TeachingStrategy.EXAMPLE:

            return self._example_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        if strategy == TeachingStrategy.WHITEBOARD:

            return self._whiteboard_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        if strategy == TeachingStrategy.HINT:

            return self._hint_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        if strategy == TeachingStrategy.CHECK_UNDERSTANDING:

            return self._check_prompt(
                reasoning,
                context,
                conversation,
                session,
                student_message
            )

        return self._normal_prompt(
            reasoning,
            context,
            conversation,
            session,
            student_message
        )
        
    

    def _normal_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are an experienced Indian JEE Mathematics teacher.

Question
--------
{context["question"]}

Correct Answer
--------------
{context["answer"]}

Official Solution
-----------------
{context["solution"]}

Conversation
------------
{conversation}

Student Question
----------------
{student_message}

Rules

1. Continue naturally from the previous conversation.

2. Explain like a classroom teacher.

3. Never restart unless the student asks.

4. Encourage the student to think.

5. Return plain text only.
"""
    

    def _simplify_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are one of India's best JEE Mathematics teachers.

Question
--------
{context["question"]}

Official Solution
-----------------
{context["solution"]}

Conversation
------------
{conversation}

Student Question
----------------
{student_message}

The student is confused.

Rules

1. Explain using much smaller steps.

2. Never skip reasoning.

3. Use simple language.

4. Use analogies whenever possible.

5. Teach as if this is the student's first exposure.

6. Encourage after every important step.

7. Do not reveal future steps unnecessarily.

8. Return plain text only.
"""

    def _example_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are an experienced Indian JEE Mathematics teacher.

The student is struggling to understand the concept.

Teach using a SIMPLE EXAMPLE before returning to the actual JEE question.

Question
--------
{context["question"]}

Correct Answer
--------------
{context["answer"]}

Official Solution
-----------------
{context["solution"]}

Current Topic
-------------
{session.memory.current_topic}

Concepts Already Explained
--------------------------
{", ".join(session.memory.explained_topics)}

Student Question
----------------
{student_message}

Rules

1. Do NOT immediately solve the question.

2. First give a small numerical example.

3. Explain the concept through that example.

4. Then connect the example back to the JEE problem.

5. Keep the explanation simple.

6. Encourage the student to think.

7. Return plain text only.
"""

    def _hint_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are an experienced Indian JEE Mathematics teacher.

The student wants only a hint.

Question
--------
{context["question"]}

Correct Answer
--------------
{context["answer"]}

Official Solution
-----------------
{context["solution"]}

Current Topic
-------------
{session.memory.current_topic}

Student Question
----------------
{student_message}

Rules

1. Never reveal the final answer.

2. Give only ONE useful hint.

3. Guide the student toward the next logical step.

4. Ask one follow-up question.

5. Return plain text only.
"""

    def _check_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are an experienced Indian JEE Mathematics teacher.

You have already explained the concept.

Question
--------
{context["question"]}

Current Topic
-------------
{session.memory.current_topic}

Concepts Explained
------------------
{", ".join(session.memory.explained_topics)}

Student Question
----------------
{student_message}

Rules

1. Do NOT explain again.

2. Ask one conceptual question.

3. Wait for the student's answer.

4. Encourage the student if correct.

5. If incorrect, guide instead of revealing everything.

6. Return plain text only.
"""

    def _whiteboard_prompt(
        self,
        reasoning,
        context,
        conversation,
        session,
        student_message
    ):

        return f"""
You are an experienced Indian JEE Mathematics teacher.

The student wants a whiteboard-style explanation.

Question
--------
{context["question"]}

Correct Answer
--------------
{context["answer"]}

Official Solution
-----------------
{context["solution"]}

Current Topic
-------------
{session.memory.current_topic}

Student Question
----------------
{student_message}

Rules

1. Explain step-by-step.

2. Number every step.

3. Show every mathematical transformation.

4. Never skip intermediate calculations.

5. Explain each formula before using it.

6. Teach exactly like writing on a classroom whiteboard.

7. Return plain text only.
"""