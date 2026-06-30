from app.services.student_session_model import (
    StudentSessionModel,
    UnderstandingLevel,
    ConfidenceLevel,
    TeachingState
)

from app.services.teacher_evaluation import (
    TeacherEvaluation
)


class StudentSessionManager:

    def __init__(self):

        self.sessions = {}

    def get_session(
        self,
        question_id: str,
        chapter: str = ""
    ) -> StudentSessionModel:

        if question_id not in self.sessions:

            self.sessions[
                question_id
            ] = StudentSessionModel(

                question_id=question_id,

                chapter=chapter
            )

        return self.sessions[
            question_id
        ]

    def remove_session(
        self,
        question_id: str
    ):

        self.sessions.pop(
            question_id,
            None
        )

    def clear(self):

        self.sessions.clear()

    # -----------------------------------------
    # Update from Teacher Evaluation
    # -----------------------------------------

    def update_from_evaluation(
        self,
        session: StudentSessionModel,
        evaluation: TeacherEvaluation
    ):

        if evaluation.student_progress == "UNDERSTOOD":

            session.understanding = UnderstandingLevel.GOOD
            session.confidence = ConfidenceLevel.HIGH

        elif evaluation.student_progress == "LEARNING":

            session.understanding = UnderstandingLevel.PARTIAL
            session.confidence = ConfidenceLevel.MEDIUM

        elif evaluation.student_progress == "STRUGGLING":

            session.understanding = UnderstandingLevel.POOR
            session.confidence = ConfidenceLevel.LOW

        session.update()

    # -----------------------------------------
    # Update Teaching State
    # -----------------------------------------

    def update_teaching_state(
        self,
        session: StudentSessionModel,
        strategy
    ):

        mapping = {

            "SIMPLIFY": TeachingState.SIMPLIFY,

            "EXAMPLE": TeachingState.EXAMPLE,

            "HINT": TeachingState.HINT,

            "CHECK_UNDERSTANDING":
                TeachingState.CHECK_UNDERSTANDING,

            "WHITEBOARD":
                TeachingState.WHITEBOARD,
        }

        session.current_teaching_state = mapping.get(

            strategy.name,

            TeachingState.EXPLAIN

        )

        session.update()