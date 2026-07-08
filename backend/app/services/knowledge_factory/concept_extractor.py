"""
MathVerse Knowledge Factory

Concept Extractor

Builds teachable mathematical concepts from
parsed chapter sections.

Version 2
---------
Deterministic.

No LLM.

No Gemini.

Consumes SectionParser output.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Concept,
)


class ConceptExtractor:
    """
    Builds Concept objects from parsed sections.
    """

    _EXCLUDED_TITLES = {
        "matrices",
        "introduction",
    }

    _QUOTE_PATTERNS = (
        "essence of mathematics",
    )

    _EXERCISE_PATTERN = re.compile(
        r"^exercise\b",
        flags=re.IGNORECASE,
    )

    def extract(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        concepts: list[Concept] = []

        seen: set[str] = set()

        for section in chapter.sections:

            title = section.title.strip()

            if not title:
                continue

            title_lower = title.lower()

            # Skip chapter title
            if title_lower in self._EXCLUDED_TITLES:
                continue

            # Skip famous quotes
            if any(pattern in title_lower for pattern in self._QUOTE_PATTERNS):
                continue

            # Skip exercises
            if self._EXERCISE_PATTERN.match(title):
                continue

            slug = self._slug(title)

            if slug in seen:
                continue

            seen.add(slug)

            description = self._first_paragraph(section.content)

            concepts.append(
                Concept(
                    concept_id=slug,
                    title=title,
                    section_number=section.number,
                    description=description,
                )
            )

        chapter.concepts = concepts

        return chapter

    @staticmethod
    def _first_paragraph(text: str) -> str:
        """
        Returns the first non-empty paragraph.
        """

        if not text:
            return ""

        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]

        if not paragraphs:
            return ""

        return paragraphs[0]

    @staticmethod
    def _slug(text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9]+",
            "-",
            text,
        )

        return text.strip("-")