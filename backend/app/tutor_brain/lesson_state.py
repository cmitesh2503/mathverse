from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LessonState(BaseModel):
    stage: str | None = None
    topic_slug: str | None = None
    topic_title: str | None = None
    summary: str = ""
    note_cards: list[str] = Field(default_factory=list)
    concept_id: str | None = None
    concept_title: str = ""
    messages: list[str] = Field(default_factory=list)
    whiteboard: dict[str, Any] = Field(default_factory=dict)
    current_question_index: int = 0

    @property
    def question_index(self) -> int:
        return self.current_question_index

    @question_index.setter
    def question_index(self, value: int) -> None:
        self.current_question_index = value
