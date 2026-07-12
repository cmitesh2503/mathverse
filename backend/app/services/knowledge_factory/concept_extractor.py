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
        "introduction",
        "summary",
        "miscellaneous exercise",
    }

    _QUOTE_PATTERNS = (
        "essence of mathematics",
    )

    _EXERCISE_PATTERN = re.compile(
        r"^(exercise|exercises|miscellaneous exercise)\b",
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
            if title_lower == chapter.metadata.title.lower():
                continue

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
                    section_id=section.section_id,
                    section_number=section.number,
                    description=description,
                    keywords=self._keywords(title),
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

        cleaned = re.sub(
            r"<!--.*?-->",
            "",
            text,
            flags=re.DOTALL,
        )

        cleaned = re.sub(
            r"={5,}",
            "",
            cleaned,
        )

        paragraphs = []

        for paragraph in cleaned.split("\n\n"):
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            if paragraph.startswith("#"):
                continue

            paragraphs.append(paragraph)

        if not paragraphs:
            return ""

        return paragraphs[0]

    @staticmethod
    def _keywords(text: str) -> list[str]:

        words = re.findall(
            r"[A-Za-z][A-Za-z0-9-]*",
            text.lower(),
        )

        return [
            word
            for word in words
            if len(word) > 2
        ]

    @staticmethod
    def _slug(text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9]+",
            "-",
            text,
        )

        return text.strip("-")
