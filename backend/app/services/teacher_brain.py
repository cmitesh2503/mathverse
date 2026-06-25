from app.services.ai_gateway import generate_response

from app.services.teaching_loop import (
    TeachingLoop,
    TeachingState,
)


class TeacherBrain:
    """
    Central AI teaching engine for MathVerse.

    Responsibilities
    ----------------
    • Build teaching prompts
    • Call AI Gateway
    • Return teacher responses

    Does NOT:
    • Access Firestore directly
    • Know FastAPI
    • Know WebSockets
    • Know frontend
    """

    def __init__(self):
        self.loop = TeachingLoop()

    def chat(
        self,
        context: dict,
        student_message: str
    ) -> str:
        """
        Explain a student's doubt.
        """
        conversation = context.get(
            "conversation",
            ""
        )
        
        state = self.loop.next_step(
            student_message
        )
        prompt = self._build_chat_prompt(
            context,
            student_message,
            conversation,
            state
        )

        return generate_response(
            prompt,
            response_schema=None
        )

    def voice_chat(
        self,
        context: dict,
        student_message: str
    ) -> str:
        """
        Voice tutor currently behaves the same
        as chat tutor.

        Later this will include spoken style,
        pauses and pronunciation improvements.
        """

        return self.chat(
            context,
            student_message
        )

    def generate_hint(
        self,
        context: dict
    ) -> str:

        prompt = f"""
You are a JEE Mathematics teacher.

Question:
{context['question']}

Give ONLY the first hint.

Do not reveal the answer.
"""

        return generate_response(
            prompt,
            response_schema=None
        )

    def _build_chat_prompt(
        self,
        context: dict,
        student_message: str,
        conversation: str,
        state: TeachingState
    ) -> str:
        if state == TeachingState.EXPLAIN:
            return self._build_explain_prompt(
                context,
                student_message,
                conversation
            )

        if state == TeachingState.CHECK_UNDERSTANDING:
            return self._build_check_prompt(
                context,
                student_message,
                conversation
            )

        if state == TeachingState.GIVE_HINT:
            return self._build_hint_prompt(
                context,
                student_message,
                conversation
            )

        return self._build_explain_prompt(
            context,
            student_message,
            conversation
        )

    def _build_explain_prompt(
        self,
        context,
        student_message,
        conversation
    ):

        return f"""
        
        You are an experienced Indian JEE Mathematics teacher.

        Question
        --------
        {context['question']}

        Correct Answer
        --------------
        {context['answer']}

        Official Solution
        -----------------
        {context['solution']}

        Previous Conversation
        ---------------------
        {conversation}

        Student Question
        ----------------
        {student_message}

        Teaching Mode
        -------------
        Explain

        Rules

        1. Explain like a classroom teacher.

        2. Answer ONLY using this uploaded JEE Mathematics question.

        3. Use the official solution as the primary source.

        4. Continue from the previous conversation naturally.

        5. Never restart the explanation unless the student asks.

        6. Refer to previous discussion whenever useful.

        7. If the student asks a follow-up question, continue teaching instead of starting over.

        8. Never answer politics.

        9. Never answer coding.

        10. Never answer movies.

        11. Never answer religion.

        12. Never answer cricket.

        13. If the question is unrelated to the uploaded JEE Mathematics problem, reply exactly:

        Let's stay focused on the uploaded JEE Mathematics problem. Ask me anything related to this question and I'll help you until you completely understand it.

        14. Encourage the student to think before revealing the next step.

        15. Behave exactly like an experienced Indian JEE coaching teacher.

        16. Return plain text only.
        """
        
    def _build_hint_prompt(
        self,
        context,
        student_message,
        conversation
    ):

        return f"""
        
        You are an experienced Indian JEE Mathematics teacher.

        Question
        --------
        {context['question']}

        Correct Answer
        --------------
        {context['answer']}

        Official Solution
        -----------------
        {context['solution']}

        Previous Conversation
        ---------------------
        {conversation}

        Student Question
        ----------------
        {student_message}

        Teaching Mode
        -------------
        Hint
        
        """
        
    def _build_check_prompt(
        self,
        context,
        student_message,
        conversation
    ):

        return f"""
        
        You are an experienced Indian JEE Mathematics teacher.

        Question
        --------
        {context['question']}

        Correct Answer
        --------------
        {context['answer']}

        Official Solution
        -----------------
        {context['solution']}

        Previous Conversation
        ---------------------
        {conversation}

        Student Question
        ----------------
        {student_message}

        Teaching Mode
        -------------
        Check Understanding  

        """