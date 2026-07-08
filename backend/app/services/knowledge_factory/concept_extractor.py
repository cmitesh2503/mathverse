"""
MathVerse Knowledge Factory

Concept Extractor

Extracts mathematical concepts from chapter markdown.

Version 1
---------
Deterministic parser.

No LLM.

No Gemini.

No Firestore.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Concept,
)


class ConceptExtractor:

    heading_pattern = re.compile(
        r"^#{1,6}\s+(.+)$",
        flags=re.MULTILINE,
    )

    def extract(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        markdown = chapter.raw_markdown

        concepts = []

        seen = set()

        for match in self.heading_pattern.finditer(markdown):

            title = match.group(1).strip()

            if len(title) < 2:
                continue

            key = title.lower()

            if key in seen:
                continue

            seen.add(key)

            concepts.append(
                Concept(
                    concept_id=self._slug(title),
                    title=title,
                )
            )

        chapter.concepts = concepts

        return chapter

    @staticmethod
    def _slug(text: str) -> str:

        text = text.lower()

        text = re.sub(r"[^a-z0-9]+", "-", text)

        return text.strip("-")