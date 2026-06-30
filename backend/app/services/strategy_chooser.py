from app.services.teaching_strategy import (
    TeachingStrategy
)


class StrategyChooser:

    def choose(
        self,
        session,
        observation,
        reasoning
    ):
        """
        Chooses the best teaching strategy.

        Inputs
        ------
        observation:
            What the teacher observed.

        reasoning:
            What the teacher inferred.

        Phase 2:
            Deterministic rules.

        Phase 4:
            Reasoning may come from Gemini,
            but this interface remains unchanged.
        """

        # ---------------------------------------
        # Use TeacherReasoning first
        # ---------------------------------------

        if reasoning.learning_stage == "STRUGGLING":
            return TeachingStrategy.SIMPLIFY

        if reasoning.next_objective == "Teach using a simple worked example":
            return TeachingStrategy.EXAMPLE

        if reasoning.next_objective == "Guide the student with a hint":
            return TeachingStrategy.HINT

        if reasoning.next_objective == "Explain using whiteboard steps":
            return TeachingStrategy.WHITEBOARD

        if reasoning.learning_stage == "UNDERSTANDING":
            return TeachingStrategy.CHECK_UNDERSTANDING

        # ---------------------------------------
        # Fallback to Observation
        # ---------------------------------------

        if observation.confused:
            return TeachingStrategy.SIMPLIFY

        if observation.needs_example:
            return TeachingStrategy.EXAMPLE

        if observation.needs_whiteboard:
            return TeachingStrategy.WHITEBOARD

        if observation.needs_hint:
            return TeachingStrategy.HINT

        if observation.understood:
            return TeachingStrategy.CHECK_UNDERSTANDING

        return TeachingStrategy.EXPLAIN