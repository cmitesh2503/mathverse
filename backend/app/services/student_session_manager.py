from app.services.student_session_model import (
    StudentSessionModel,
    UnderstandingLevel,
    ConfidenceLevel,
    TeachingState,
    LessonStage
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

    # -----------------------------------------
    # Lesson State
    # -----------------------------------------

    def start_lesson(
        self,
        session: StudentSessionModel,
        lesson_id: str,
        current_concept: str = ""
    ):
        """
        Initialize lesson-level state for an existing session.

        This does not change the existing question-tutoring state.
        """

        session.lesson_id = lesson_id
        session.concept_index = 0
        session.current_concept = current_concept
        session.lesson_stage = LessonStage.CHAPTER_INTRO

        session.update()

    def set_current_concept(
        self,
        session: StudentSessionModel,
        current_concept: str
    ):
        """
        Set the current lesson concept without changing
        the lesson stage or concept index.
        """

        session.current_concept = current_concept

        session.update()

    def advance_lesson_stage(
        self,
        session: StudentSessionModel
    ):
        """
        Advance the lesson through the deterministic stage sequence.

        The final SUMMARY stage is terminal and remains SUMMARY
        when advanced again.
        """

        stage_order = [
            LessonStage.CHAPTER_INTRO,
            LessonStage.CONCEPT_EXPLANATION,
            LessonStage.UNDERSTANDING_CHECK,
            LessonStage.WORKED_EXAMPLE,
            LessonStage.STUDENT_PRACTICE,
            LessonStage.EXERCISE,
            LessonStage.SUMMARY,
        ]

        current_index = stage_order.index(
            session.lesson_stage
        )

        if current_index < len(stage_order) - 1:

            session.lesson_stage = stage_order[
                current_index + 1
            ]

            session.update()

    def advance_concept(
        self,
        session: StudentSessionModel
    ):
        """
        Advance the lesson concept index.

        This method intentionally does not decide which concept
        comes next. Curriculum selection will be handled later.
        """

        session.concept_index += 1

        session.update()
