from dataclasses import dataclass


@dataclass
class TeachingState:
    """
    Represents what the teacher is currently doing.

    Unlike TeacherMemory, this is not knowledge.

    It represents the current teaching activity.
    """

    strategy: str = ""

    objective: str = ""

    current_step: int = 0

    explanation_count: int = 0

    hint_count: int = 0

    example_count: int = 0

    whiteboard_count: int = 0

    last_strategy: str = ""

    last_hint: str = ""

    last_example: str = ""

    last_explanation: str = ""