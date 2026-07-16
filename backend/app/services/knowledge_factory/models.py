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
    
@dataclass(slots=True)
class HeadingCandidate:
    """
    Candidate heading detected in the markdown.

    The parser first detects many possible headings,
    assigns a confidence score, then keeps only the
    strongest candidates.
    """

    start: int
    end: int

    number: str
    title: str

    level: int

    score: float