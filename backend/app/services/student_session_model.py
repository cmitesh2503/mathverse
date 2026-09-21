from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.services.teacher_memory import TeacherMemory


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UnderstandingLevel(str, Enum):
    POOR = "poor"
    PARTIAL = "partial"
    GOOD = "good"
    MASTERED = "mastered"


class TeachingState(str, Enum):
    EXPLAIN = "explain"
    SIMPLIFY = "simplify"
    EXAMPLE = "example"
    HINT = "hint"
    CHECK_UNDERSTANDING = "check_understanding"
    WHITEBOARD = "whiteboard"


class LessonStage(str, Enum):
    CHAPTER_INTRO = "chapter_intro"
    CONCEPT_EXPLANATION = "concept_explanation"
    UNDERSTANDING_CHECK = "understanding_check"
    WORKED_EXAMPLE = "worked_example"
    STUDENT_PRACTICE = "student_practice"
    EXERCISE = "exercise"
    SUMMARY = "summary"


@dataclass
class StudentSessionModel:
    """
    Represents the AI teacher's understanding of
    the student during the CURRENT tutoring session.

    This object lives only in memory.

    Later we will combine it with StudentProfile
    stored in Firestore.
    """

    question_id: str
    chapter: str

    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    understanding: UnderstandingLevel = UnderstandingLevel.PARTIAL

    followup_questions: int = 0

    hints_used: int = 0

    explanations_given: int = 0

    checks_performed: int = 0

    current_teaching_state: TeachingState = field(
        default=TeachingState.EXPLAIN
    )
    
    # Additive lesson-level state.
    # Existing question-tutoring behavior remains unchanged.
    lesson_id: str = ""

    current_concept: str = ""

    concept_index: int = 0

    lesson_stage: LessonStage = LessonStage.CHAPTER_INTRO

    started_at: datetime = field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = field(
        default_factory=datetime.utcnow
    )

    memory: TeacherMemory = field(
        default_factory=TeacherMemory
    )

    def update(self):
        self.updated_at = datetime.utcnow()

    def record_followup(self):
        self.followup_questions += 1
        self.update()

    def record_hint(self):
        self.hints_used += 1
        self.update()

    def record_explanation(self):
        self.explanations_given += 1
        self.update()

    def record_understanding_check(self):
        self.checks_performed += 1
        self.update()
        
    