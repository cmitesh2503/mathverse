from app.services.ai_gateway import generate_response

from app.services.teaching_loop import (
    TeachingLoop,
    TeachingState,
)
from app.services.student_session_manager import (
    StudentSessionManager
)
from app.services.memory_updater import (
    MemoryUpdater
)
from app.services.strategy_chooser import (
    StrategyChooser
)
from app.services.teacher_observer import (
    TeacherObserver
)
from app.services.prompt_builder import PromptBuilder

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
        self.session_manager = StudentSessionManager()
        self.memory_updater = MemoryUpdater()
        self.strategy = StrategyChooser()
        self.observer = TeacherObserver()
        self.prompt_builder = PromptBuilder()
        
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
        
        session = self.session_manager.get_session(

    question_id=context["question_id"],

            chapter=context.get(
                "chapter",
                ""
            )
        )
        memory = session.memory
        
        print(session.memory) # Temporary add remove after test
        
        self.observer.observe(
            session,
            student_message
        )
        
        observation = self.observer.observe(
            session,
            student_message
        )

        print(observation)

        strategy = self.strategy.choose(
            session,
            observation
        )
        print(strategy) # Temporary add remove after test
        
        session.record_followup()

        state = self.loop.next_step(

            student_message
        )
        
        prompt = self._build_chat_prompt(
            context,
            student_message,
            conversation,
            state,
            memory
        )
        
        prompt = self.prompt_builder.build(
            strategy,
            context,
            session,
            student_message
        )
        
        session.current_teaching_state = state.value

        session.record_explanation()
        
        print(session) # Temporary add remove after test

        
        response = generate_response(
            prompt,
            response_schema=None
        )

        self.memory_updater.update(
            session,
            student_message,
            response
        )

        print(session)

        return response

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
        state: TeachingState,
        memory
    ) -> str:
        if state == TeachingState.EXPLAIN:
            return self._build_explain_prompt(
                context,
                student_message,
                conversation,
                memory
            )
        

        if state == TeachingState.CHECK_UNDERSTANDING:
            return self._build_check_prompt(
                context,
                student_message,
                conversation,
                memory
            )

        if state == TeachingState.GIVE_HINT:
            return self._build_hint_prompt(
                context,
                student_message,
                conversation
            )

        return self._build_explain_prompt(
            self,
            context,
            student_message,
            conversation,
            memory
            
        )

    def _build_explain_prompt(
        self,
        context,
        student_message,
        conversation,
        memory
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
        
        Teacher Memory
        --------------
        Current Topic:
        {memory.current_topic}

        Previously Explained:
        {memory.explained_topics}

        Student Questions:
        {memory.student_questions}

        Known Misconceptions:
        {memory.misconceptions}

        Rules

        1. Explain like a classroom teacher.

        2. Answer ONLY using this uploaded JEE Mathematics question.

        3. Use the official solution as the primary source.

        4. Continue from the previous conversation naturally.

        5. Never restart the explanation unless the student asks.

        6. Refer to previous discussion whenever useful.

        7. If the student asks a follow-up question, continue teaching instead of starting over.
        
        8. Do NOT repeat explanations already given unless the student is still confused.

        9. If the student's new question relates to a previous explanation, continue naturally instead of starting from the beginning.

        10. Build on previous explanations instead of repeating them.

        11. Never answer politics.

        12. Never answer coding.

        13. Never answer movies.

        14. Never answer religion.

        15. Never answer cricket.

        16. If the question is unrelated to the uploaded JEE Mathematics problem, reply exactly:

        Let's stay focused on the uploaded JEE Mathematics problem. Ask me anything related to this question and I'll help you until you completely understand it.

        17. Encourage the student to think before revealing the next step.

        18. Behave exactly like an experienced Indian JEE coaching teacher.

        19. Return plain text only.
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
        conversation,
        memory
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