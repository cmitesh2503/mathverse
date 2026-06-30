from app.services.teacher_evaluation import (
    TeacherEvaluation
)


class TeacherEvaluator:
    """
    Evaluates whether the current teaching interaction
    achieved its objective.

    Teaching Lifecycle

        Observe
            ↓
        Think
            ↓
        Choose Strategy
            ↓
        Teach
            ↓
        Evaluate   <-- This class
            ↓
        Adapt
            ↓
        Repeat

    Phase 2
    -------
    Uses deterministic Python rules.

    Phase 4
    -------
    May internally use Gemini while keeping the
    public interface unchanged.
    """

    def evaluate(
        self,
        context,
        session,
        observation,
        reasoning,
        strategy,
        teacher_response: str,
    ) -> TeacherEvaluation:

        evaluation = TeacherEvaluation()

        # ------------------------------------
        # Student Understanding
        # ------------------------------------

        if observation.understood:

            evaluation.teaching_success = True

            evaluation.student_progress = "UNDERSTOOD"

            evaluation.confidence = 0.95

            evaluation.next_recommendation = (
                "Proceed to the next concept."
            )

        elif observation.confused:

            evaluation.teaching_success = False

            evaluation.student_progress = "STRUGGLING"

            evaluation.confidence = 0.90

        else:

            evaluation.student_progress = "IN_PROGRESS"

            evaluation.confidence = 0.60

        # ------------------------------------
        # Strategy Effectiveness
        # ------------------------------------

        if (
            observation.confused
            and strategy.name == "HINT"
        ):

            evaluation.should_change_strategy = True

            evaluation.next_recommendation = (
                "Use a worked example."
            )

        elif (
            observation.confused
            and strategy.name == "EXAMPLE"
        ):

            evaluation.should_change_strategy = True

            evaluation.next_recommendation = (
                "Simplify the explanation."
            )

        elif (
            observation.confused
            and strategy.name == "SIMPLIFY"
        ):

            evaluation.should_change_strategy = False

            evaluation.next_recommendation = (
                "Continue simplified teaching."
            )

        elif observation.understood:

            evaluation.should_change_strategy = False

        # ------------------------------------
        # Teacher Notes
        # ------------------------------------

        evaluation.notes = (
            "Generated using deterministic evaluation rules."
        )

        return evaluation