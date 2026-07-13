import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
)
from app.services.knowledge_factory.concept_extractor import ConceptExtractor
from app.services.knowledge_factory.example_extractor import ExampleExtractor
from app.services.knowledge_factory.section_parser import SectionParser


def _chapter(markdown: str) -> ChapterKnowledge:
    return ChapterKnowledge(
        metadata=ChapterMetadata(
            chapter_id="chapter-007",
            curriculum_id="jee-main-2026-mathematics",
            order=7,
            title="Coordinate Geometry",
            slug="coordinate-geometry",
            exam="JEE Main",
            subject="Mathematics",
            grade="11",
            version="2026",
        ),
        raw_markdown=markdown,
    )


def _extract(markdown: str) -> ChapterKnowledge:
    chapter = SectionParser().parse(
        _chapter(markdown)
    )
    chapter = ConceptExtractor().extract(chapter)
    return ExampleExtractor().extract(chapter)


def test_example_extractor_extracts_worked_examples_and_links_them():
    chapter = _extract(
        """
# Coordinate Geometry

## 7.2 Distance Formula

Use the distance formula to compare two points.

Example 1: Find the distance between P(1, 2) and Q(4, 6).
Solution: Use the distance formula.
d = sqrt((4 - 1)^2 + (6 - 2)^2)
Therefore d = 5.

### 7.2.1 Midpoint Method

Worked Example 2
Problem: Find the midpoint of A(0, 0) and B(2, 4).
Solution:
Midpoint = ((0 + 2) / 2, (0 + 4) / 2)
= (1, 2)

## Exercise 7.2

Example 3: This should not be treated as a teaching example.
Solution: Exercises are handled by ExerciseExtractor.
"""
    )

    examples = {
        example.example_id: example
        for example in chapter.examples
    }
    sections = {
        section.section_id: section
        for section in chapter.sections
    }
    concepts = {
        concept.concept_id: concept
        for concept in chapter.concepts
    }

    assert list(examples) == [
        "7-2-distance-formula-example-001",
        "7-2-1-midpoint-method-example-001",
    ]

    distance = examples["7-2-distance-formula-example-001"]
    assert distance.title == "Example 1"
    assert distance.problem == (
        "Find the distance between P(1, 2) and Q(4, 6)."
    )
    assert distance.solution == (
        "Use the distance formula.\n"
        "d = sqrt((4 - 1)^2 + (6 - 2)^2)\n"
        "Therefore d = 5."
    )
    assert distance.section_id == "7-2-distance-formula"
    assert distance.concept_ids == ["distance-formula"]

    midpoint = examples["7-2-1-midpoint-method-example-001"]
    assert midpoint.title == "Worked Example 2"
    assert midpoint.problem == "Find the midpoint of A(0, 0) and B(2, 4)."
    assert midpoint.solution == (
        "Midpoint = ((0 + 2) / 2, (0 + 4) / 2)\n"
        "= (1, 2)"
    )
    assert midpoint.section_id == "7-2-1-midpoint-method"
    assert midpoint.concept_ids == ["midpoint-method"]

    assert sections["7-2-distance-formula"].example_ids == [
        "7-2-distance-formula-example-001",
    ]
    assert sections["7-2-1-midpoint-method"].example_ids == [
        "7-2-1-midpoint-method-example-001",
    ]
    assert sections["exercise-7-2"].example_ids == []

    assert concepts["distance-formula"].examples == [
        "7-2-distance-formula-example-001",
    ]
    assert concepts["midpoint-method"].examples == [
        "7-2-1-midpoint-method-example-001",
    ]


def test_example_extractor_skips_incomplete_examples():
    chapter = _extract(
        """
# Coordinate Geometry

## 7.2 Distance Formula

Example 1: Find the distance between two points.
"""
    )

    assert chapter.examples == []
    assert chapter.sections[1].example_ids == []
    assert chapter.concepts[0].examples == []
