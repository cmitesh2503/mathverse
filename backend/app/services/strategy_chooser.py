from app.services.teaching_strategy import (
    TeachingStrategy
)


class StrategyChooser:

    def choose(
        self,
        session,
        observation
    ):

        # Student is confused
        if observation.confused:
            return TeachingStrategy.SIMPLIFY

        # Wants a worked example
        if observation.needs_example:
            return TeachingStrategy.EXAMPLE

        # Wants a drawing
        if observation.needs_whiteboard:
            return TeachingStrategy.WHITEBOARD

        # Wants only a hint
        if observation.needs_hint:
            return TeachingStrategy.HINT

        # Student already understands
        if observation.understood:
            return TeachingStrategy.CHECK_UNDERSTANDING

        return TeachingStrategy.EXPLAIN