from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class Concept(BaseModel):

    id: str

    name: str

    chapter_id: str

    order: int

    prerequisites: List[str] = Field(default_factory=list)


class Formula(BaseModel):

    id: str

    chapter_id: str

    order: int

    latex: str

    variables: List[str] = Field(default_factory=list)

    description: str = ""

    meaning: str = ""

    concept_ids: List[str] = Field(default_factory=list)


class Example(BaseModel):

    id: str

    chapter_id: str

    order: int

    title: str

    problem: str

    solution: str

    difficulty: str = "Medium"

    concept_ids: List[str] = Field(default_factory=list)


class Exercise(BaseModel):

    id: str

    chapter_id: str

    order: int

    title: str = ""

    source: str = ""

    question: str

    question_type: str = "question"

    options: List[str] = Field(default_factory=list)

    answer: str = ""

    marks: Optional[int] = None

    difficulty: str = "Medium"

    concept_ids: List[str] = Field(default_factory=list)


class Chapter(BaseModel):

    id: str

    name: str

    order: int

    concepts: List[Concept] = Field(default_factory=list)

    formulas: List[Formula] = Field(default_factory=list)

    examples: List[Example] = Field(default_factory=list)

    exercises: List[Exercise] = Field(default_factory=list)

class Curriculum(BaseModel):

    exam: str

    subject: str

    grade: str

    chapters: List[Chapter] = Field(default_factory=list)


class ExtractionResult(BaseModel):

    success: bool = True

    document_type: str

    metadata: Dict = Field(default_factory=dict)

    data: Dict = Field(default_factory=dict)

    warnings: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):

    valid: bool

    errors: List[str] = Field(default_factory=list)


class KnowledgeGraphResult(BaseModel):

    nodes_created: int = 0

    relationships_created: int = 0
