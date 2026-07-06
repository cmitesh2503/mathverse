from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class Chapter:

    id: str
    order: int
    title: str
    description: str = ""


@dataclass
class Curriculum:

    curriculum_id: str
    exam: str
    subject: str
    grade: str
    version: str

    chapters: List[Chapter] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)