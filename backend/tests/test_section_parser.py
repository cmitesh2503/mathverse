import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
)
from app.services.knowledge_factory.concept_extractor import ConceptExtractor
from app.services.knowledge_factory.section_parser import SectionParser


def _chapter(markdown: str) -> ChapterKnowledge:
    return ChapterKnowledge(
        metadata=ChapterMetadata(
            chapter_id="chapter-003",
            curriculum_id="jee-main-2026-mathematics",
            order=3,
            title="Matrices",
            slug="matrices",
            exam="JEE Main",
            subject="Mathematics",
            grade="11",
            version="2026",
        ),
        raw_markdown=markdown,
    )


def test_section_parser_preserves_full_content_and_hierarchy():
    chapter = SectionParser().parse(
        _chapter(
            """
# Matrices

Chapter introduction.

## 3.1 Matrix

A matrix is a rectangular arrangement of numbers.

### 3.1.1 Order of a Matrix

Rows and columns define the order.

## 3.2 Types of Matrices

Square and diagonal matrices are common types.
"""
        )
    )

    sections = {
        section.section_id: section
        for section in chapter.sections
    }

    root = sections["matrices"]
    matrix = sections["3-1-matrix"]
    order = sections["3-1-1-order-of-a-matrix"]
    types = sections["3-2-types-of-matrices"]

    assert root.parent is None
    assert root.children == [
        "3-1-matrix",
        "3-2-types-of-matrices",
    ]
    assert matrix.parent == "matrices"
    assert matrix.children == ["3-1-1-order-of-a-matrix"]
    assert order.parent == "3-1-matrix"
    assert types.parent == "matrices"

    assert "### 3.1.1 Order of a Matrix" in matrix.content
    assert "## 3.2 Types of Matrices" not in matrix.content
    assert "Rows and columns define the order." in order.content

    assert matrix.concept_ids == []
    assert matrix.formula_ids == []
    assert matrix.example_ids == []
    assert matrix.exercise_ids == []
    assert matrix.figure_ids == []
    assert matrix.teacher_script_ids == []
    assert matrix.whiteboard_ids == []


def test_concept_extractor_links_concepts_back_to_sections():
    chapter = SectionParser().parse(
        _chapter(
            """
# Matrices

## 3.1 Matrix

A matrix is a rectangular arrangement of numbers.

## Exercise 3.1

Find the order of the given matrix.
"""
        )
    )

    chapter = ConceptExtractor().extract(chapter)

    concepts = {
        concept.concept_id: concept
        for concept in chapter.concepts
    }
    sections = {
        section.section_id: section
        for section in chapter.sections
    }

    assert list(concepts) == ["matrix"]
    assert sections["3-1-matrix"].concept_ids == ["matrix"]
    assert sections["exercise-3-1"].concept_ids == []

    concept = concepts["matrix"]
    assert concept.section_id == "3-1-matrix"
    assert concept.section_number == "3.1"
    assert concept.chapter_id == "chapter-003"
    assert concept.curriculum_id == "jee-main-2026-mathematics"
    assert concept.learning_objectives == []
