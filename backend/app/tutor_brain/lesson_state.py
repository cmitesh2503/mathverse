from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LessonState:
    step: str = "INTRO"
    grade: int = 10
    topic_slug: str = ""
    topic_title: str = ""
    current_concept_id: str = ""
    current_concept_title: str = ""
    current_concept: dict | None = None
    correct_answers_in_concept: int = 0
    total_attempts: int = 0
    mastery_threshold: int = 2
    current_question_index: int = 0
    last_answer_correct: bool = False
    homework_given: bool = False
    notes: list[str] = field(default_factory=list)
    last_summary: str = ""
    whiteboard: dict = field(default_factory=dict)
    start_time: datetime | None = None
    break_taken: bool = False

    @property
    def question_index(self) -> int:
        return self.current_question_index

    @question_index.setter
    def question_index(self, value: int) -> None:
        self.current_question_index = value
