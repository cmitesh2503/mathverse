from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    document_id: str
    title: str
    source: str
    publisher: Optional[str] = None
    board: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    version: str = "1.0"


class LearningObjective(BaseModel):
    id: str
    description: str


class Prerequisite(BaseModel):
    id: str
    description: str


class Formula(BaseModel):
    id: str
    latex: str
    description: Optional[str] = None


class Definition(BaseModel):
    id: str
    title: str
    text: str


class Property(BaseModel):
    id: str
    title: str
    text: str


class Theorem(BaseModel):
    id: str
    title: str
    statement: str
    proof: Optional[str] = None


class Figure(BaseModel):
    id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    image_reference: Optional[str] = None


class Table(BaseModel):
    id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    markdown: Optional[str] = None


class Example(BaseModel):
    id: str
    title: Optional[str] = None
    problem: str
    solution: Optional[str] = None
    example_type: Optional[str] = None


class ExerciseQuestion(BaseModel):
    id: str
    number: Optional[str] = None
    question: str
    difficulty: Optional[str] = None
    marks: Optional[int] = None


class Concept(BaseModel):
    id: str
    title: str
    explanation: str

    definitions: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    theorems: List[str] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

    prerequisites: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)


class Subsection(BaseModel):
    id: str
    number: Optional[str] = None
    title: str

    concepts: List[Concept] = Field(default_factory=list)

    definitions: List[Definition] = Field(default_factory=list)

    properties: List[Property] = Field(default_factory=list)

    theorems: List[Theorem] = Field(default_factory=list)

    formulas: List[Formula] = Field(default_factory=list)

    examples: List[Example] = Field(default_factory=list)

    exercises: List[ExerciseQuestion] = Field(default_factory=list)

    figures: List[Figure] = Field(default_factory=list)

    tables: List[Table] = Field(default_factory=list)


class Section(BaseModel):
    id: str
    number: Optional[str] = None
    title: str
    subsections: List[Subsection] = Field(default_factory=list)


class Chapter(BaseModel):
    id: str
    number: Optional[str] = None
    title: str
    sections: List[Section] = Field(default_factory=list)


class Relationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str


class Curriculum(BaseModel):
    id: str
    title: str


class KnowledgeDocument(BaseModel):
    metadata: Metadata

    curriculum: Curriculum

    chapters: List[Chapter] = Field(default_factory=list)

    learning_objectives: List[LearningObjective] = Field(default_factory=list)

    prerequisites: List[Prerequisite] = Field(default_factory=list)

    relationships: List[Relationship] = Field(default_factory=list)

    extensions: Dict[str, object] = Field(default_factory=dict)