"""
MathVerse Knowledge Factory

Canonical domain models for chapter knowledge.

These models are shared by:
- Azure Document Intelligence Parser
- Firestore Writer
- Knowledge Factory
- RAG Indexer
- Teacher Brain
- Question Generator
- Hint Generator

NOTE:
This file contains DATA MODELS ONLY.
Do not add parsing, Firestore, or business logic here.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================
# Chapter Metadata
# ============================================================

@dataclass
class ChapterMetadata:
    chapter_id: str
    curriculum_id: str

    order: int

    title: str
    slug: str

    exam: str
    subject: str
    grade: str
    version: str

    summary: str = ""

@dataclass
class Section:
    """
    Canonical representation of one chapter section.

    All downstream extractors operate on sections
    instead of reparsing raw markdown.
    """

    section_id: str
    number: str
    title: str
    level: int
    content: str
    section_type: str = "content"
# ============================================================
# Learning Objectives
# ============================================================

@dataclass
class LearningObjective:
    objective_id: str
    description: str


# ============================================================
# Concept
# ============================================================

@dataclass
class Concept:
    concept_id: str

    name: str

    definition: str

    explanation: str = ""

    keywords: List[str] = field(default_factory=list)


# ============================================================
# Formula
# ============================================================

@dataclass
class Formula:
    formula_id: str

    title: str

    latex: str

    explanation: str = ""

    conditions: str = ""


# ============================================================
# Worked Example
# ============================================================

@dataclass
class Example:
    example_id: str

    title: str

    problem: str

    solution: str

    difficulty: str = "Medium"


# ============================================================
# Exercise
# ============================================================

@dataclass
class Exercise:
    exercise_id: str

    question: str

    marks: Optional[int] = None

    difficulty: str = "Medium"

    solution_available: bool = False


# ============================================================
# Previous Year Question (PYQ)
# ============================================================

@dataclass
class PYQ:
    pyq_id: str

    year: int

    exam: str

    question: str

    marks: Optional[int] = None

    solution: str = ""


# ============================================================
# Figure / Diagram
# ============================================================

@dataclass
class Figure:
    figure_id: str

    caption: str

    image_path: str

    description: str = ""


# ============================================================
# Student Misconception
# ============================================================

@dataclass
class Misconception:
    misconception_id: str

    statement: str

    correction: str


# ============================================================
# Prerequisite
# ============================================================

@dataclass
class Prerequisite:
    prerequisite_id: str

    chapter_slug: str

    topic: str


# ============================================================
# Embedding Reference
# ============================================================

@dataclass
class EmbeddingReference:
    embedding_id: str

    chunk_id: str

    vector_document: str


# ============================================================
# Complete Chapter Knowledge
# ============================================================

@dataclass
class ChapterKnowledge:

    metadata: ChapterMetadata

    raw_markdown: str = ""
    
    sections: list[Section] = field(default_factory=list)

    learning_objectives: List[LearningObjective] = field(default_factory=list)

    concepts: List[Concept] = field(default_factory=list)

    formulas: List[Formula] = field(default_factory=list)

    examples: List[Example] = field(default_factory=list)

    exercises: List[Exercise] = field(default_factory=list)

    pyqs: List[PYQ] = field(default_factory=list)

    figures: List[Figure] = field(default_factory=list)

    misconceptions: List[Misconception] = field(default_factory=list)

    prerequisites: List[Prerequisite] = field(default_factory=list)

    embeddings: List[EmbeddingReference] = field(default_factory=list)
    
@dataclass
class Concept:

    concept_id: str

    title: str

    description: str = ""

    keywords: List[str] = field(default_factory=list)

    aliases: List[str] = field(default_factory=list)

    difficulty: str = "medium"

    prerequisites: List[str] = field(default_factory=list)