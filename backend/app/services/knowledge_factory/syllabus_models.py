from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SyllabusTopic:
    topic_id: str
    order: int
    title: str
    subtopics: list[str] = field(default_factory=list)
    curriculum_chapter_id: str = ""
    curriculum_section_ids: list[str] = field(default_factory=list)
    curriculum_concept_ids: list[str] = field(default_factory=list)


@dataclass
class SyllabusChapter:
    chapter_id: str
    order: int
    title: str
    topics: list[SyllabusTopic] = field(default_factory=list)


@dataclass
class Syllabus:
    syllabus_id: str
    board: str
    grade: str
    subject: str
    version: str
    source_path: str = ""
    chapters: list[SyllabusChapter] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
