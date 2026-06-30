from dataclasses import dataclass
from typing import Optional


@dataclass
class TeacherEvaluation:
    """
    Represents the teacher's evaluation of the
    current teaching cycle.

    Produced after the AI has responded.

    Phase 2:
        Deterministic Python evaluation.

    Phase 4:
        Gemini-assisted evaluation.

    This object is transient and is not persisted.
    """

    teaching_success: bool = False

    student_progress: str = "UNKNOWN"

    should_change_strategy: bool = False

    next_recommendation: Optional[str] = None

    confidence: float = 0.0

    notes: Optional[str] = None