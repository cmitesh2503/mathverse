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

        Phase 2:
            Deterministic rules.

        Phase 3:
            Uses previous teaching methods to
            avoid repeating the same strategy.
        """

        used_methods = {
            method.upper().replace(" ", "_")
            for method in session.memory.teaching_methods_used
        }

        def already_used(strategy: TeachingStrategy) -> bool:
            return strategy.name in used_methods

        # ---------------------------------------
        # Student is struggling
        # ---------------------------------------

        if reasoning.learning_stage == "STRUGGLING":

            if not already_used(TeachingStrategy.SIMPLIFY):
                return TeachingStrategy.SIMPLIFY

            if not already_used(TeachingStrategy.EXAMPLE):
                return TeachingStrategy.EXAMPLE

            if not already_used(TeachingStrategy.WHITEBOARD):
                return TeachingStrategy.WHITEBOARD

            if not already_used(TeachingStrategy.HINT):
                return TeachingStrategy.HINT

            return TeachingStrategy.EXPLAIN

        # ---------------------------------------
        # TeacherReasoning objectives
        # ---------------------------------------

        if reasoning.next_objective == "Teach using a simple worked example":

            if not already_used(TeachingStrategy.EXAMPLE):
                return TeachingStrategy.EXAMPLE

        if reasoning.next_objective == "Guide the student with a hint":

            if not already_used(TeachingStrategy.HINT):
                return TeachingStrategy.HINT

        if reasoning.next_objective == "Explain using whiteboard steps":

            if not already_used(TeachingStrategy.WHITEBOARD):
                return TeachingStrategy.WHITEBOARD

        if reasoning.learning_stage == "UNDERSTANDING":
            return TeachingStrategy.CHECK_UNDERSTANDING

        # ---------------------------------------
        # Fallback to Observation
        # ---------------------------------------

        if observation.confused:

            if not already_used(TeachingStrategy.SIMPLIFY):
                return TeachingStrategy.SIMPLIFY

            if not already_used(TeachingStrategy.EXAMPLE):
                return TeachingStrategy.EXAMPLE

            return TeachingStrategy.WHITEBOARD

        if observation.needs_example:

            if not already_used(TeachingStrategy.EXAMPLE):
                return TeachingStrategy.EXAMPLE

            return TeachingStrategy.WHITEBOARD

        if observation.needs_whiteboard:

            if not already_used(TeachingStrategy.WHITEBOARD):
                return TeachingStrategy.WHITEBOARD

            return TeachingStrategy.SIMPLIFY

        if observation.needs_hint:

            if not already_used(TeachingStrategy.HINT):
                return TeachingStrategy.HINT

            return TeachingStrategy.EXAMPLE

        if observation.understood:
            return TeachingStrategy.CHECK_UNDERSTANDING

        return TeachingStrategy.EXPLAIN