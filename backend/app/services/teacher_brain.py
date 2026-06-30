from app.services.ai_gateway import generate_response


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
from app.services.teacher_reasoner import (
    TeacherReasoner
)
from app.services.teacher_evaluator import (
    TeacherEvaluator
)
from app.services.teaching_state import TeachingState

class TeacherBrain:
    """
    Central AI teaching engine for MathVerse.

    Responsibilities
    ----------------
    • Coordinate the teaching pipeline
    • Call AI Gateway
    • Return teacher responses

    Does NOT:
    • Access Firestore directly
    • Know FastAPI
    • Know WebSockets
    • Know frontend
    """

    def __init__(self):
        
        self.session_manager = StudentSessionManager()
        self.memory_updater = MemoryUpdater()
        self.strategy = StrategyChooser()
        self.observer = TeacherObserver()
        self.prompt_builder = PromptBuilder()
        self.reasoner = TeacherReasoner()
        self.evaluator = TeacherEvaluator()
        
    def chat(
        self,
        context: dict,
        student_message: str
    ) -> str:
        """
        Explain a student's doubt.
        """
        
        
        session = self.session_manager.get_session(

    question_id=context["question_id"],

            chapter=context.get(
                "chapter",
                ""
            )
        )
        
        
        print(session.memory) # Temporary add remove after test
        
               
        observation = self.observer.observe(
            session,
            student_message
        )
        print("\n========== OBSERVATION ==========")
        print(observation) # Temporary add remove after test    
        
        reasoning = self.reasoner.reason(
            context=context,
            session=session,
            memory=session.memory,
            observation=observation
        )

        print("\n========== REASONING ==========")
        print(reasoning)

        strategy = self.strategy.choose(
            session,
            observation,
            reasoning
        )
        print("\n========== STRATEGY ==========")
        print(strategy) # Temporary add remove after test
        
        
        
        session.record_followup()
        

        
        
                
        prompt = self.prompt_builder.build(
            strategy,
            context,
            session,
            student_message
        )
        
        
        session.record_explanation()
        
        print(session) # Temporary add remove after test

        
        response = generate_response(
            prompt,
            response_schema=None
        )
        
        evaluation = self.evaluator.evaluate(
            context=context,
            session=session,
            observation=observation,
            reasoning=reasoning,
            strategy=strategy,
            teacher_response=response,
        )
        
        print("\n========== EVALUATION ==========")
        print(evaluation)

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
