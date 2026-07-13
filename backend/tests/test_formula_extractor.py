import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
)
from app.services.knowledge_factory.concept_extractor import ConceptExtractor
from app.services.knowledge_factory.formula_extractor import FormulaExtractor
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
    return FormulaExtractor().extract(chapter)


def test_formula_extractor_extracts_latex_and_links_section_and_concept():
    chapter = _extract(
        r"""
# Coordinate Geometry

Introductory text.

## 7.2 Distance Formula

The distance formula is:

$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

Use the result to find distance in coordinate geometry.
"""
    )

    sections = {
        section.section_id: section
        for section in chapter.sections
    }
    concepts = {
        concept.concept_id: concept
        for concept in chapter.concepts
    }

    assert len(chapter.formulas) == 1

    formula = chapter.formulas[0]

    assert formula.formula_id == "7-2-distance-formula-formula-001"
    assert formula.title == "Distance Formula"
    assert formula.latex == r"d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}"
    assert formula.meaning == "The distance formula is:"
    assert formula.variables == [
        "d",
        "x_2",
        "x_1",
        "y_2",
        "y_1",
    ]
    assert formula.section_id == "7-2-distance-formula"
    assert formula.concept_ids == ["distance-formula"]

    assert sections["7-2-distance-formula"].formula_ids == [
        "7-2-distance-formula-formula-001",
    ]
    assert concepts["distance-formula"].formula_ids == [
        "7-2-distance-formula-formula-001",
    ]


def test_formula_extractor_uses_local_section_content_and_skips_exercises():
    chapter = _extract(
        """
# Coordinate Geometry

## 7.3 Area Formula

Area of a circle:

A = πr²

### 7.3.1 Commutative Identity

Use this identity:

x + y = y + x

## Exercise 7.3

x + y = 10
"""
    )

    formulas = {
        formula.formula_id: formula
        for formula in chapter.formulas
    }
    sections = {
        section.section_id: section
        for section in chapter.sections
    }

    assert list(formulas) == [
        "7-3-area-formula-formula-001",
        "7-3-1-commutative-identity-formula-001",
    ]
    assert formulas["7-3-area-formula-formula-001"].latex == r"A = \pi r^2"
    assert formulas["7-3-area-formula-formula-001"].section_id == (
        "7-3-area-formula"
    )
    assert formulas["7-3-1-commutative-identity-formula-001"].section_id == (
        "7-3-1-commutative-identity"
    )

    assert sections["7-3-area-formula"].formula_ids == [
        "7-3-area-formula-formula-001",
    ]
    assert sections["7-3-1-commutative-identity"].formula_ids == [
        "7-3-1-commutative-identity-formula-001",
    ]
    assert sections["exercise-7-3"].formula_ids == []
