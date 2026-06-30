from dataclasses import dataclass
from typing import Optional


@dataclass
class TeacherReasoning:
    """
    Represents the teacher's internal reasoning for a
    single teaching cycle.

    This object is NOT persisted.

    Phase 2:
        Produced by deterministic Python rules.

    Phase 4:
        Produced by Gemini while keeping the same interface.
    """

    student_goal: Optional[str] = None

    probable_misconception: Optional[str] = None

    learning_stage: str = "UNKNOWN"

    next_objective: Optional[str] = None

    recommended_depth: str = "NORMAL"

    confidence: float = 0.0

    notes: Optional[str] = None