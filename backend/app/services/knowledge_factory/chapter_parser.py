"""
MathVerse Knowledge Factory

Chapter Parser

Converts Azure Document Intelligence Layout JSON
into ChapterKnowledge.

This parser intentionally extracts only:
- metadata
- markdown
- chapter summary

Specialized extractors (ConceptExtractor,
FormulaExtractor, ExerciseExtractor, etc.)
will populate the remaining collections.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
)


class ChapterParser:

    def parse(self, json_path: str | Path) -> ChapterKnowledge:

        json_path = Path(json_path)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        result = data["analyzeResult"]

        markdown = result.get("content", "")

        metadata = self._extract_metadata(markdown)
        
        chapter = ChapterKnowledge(
            metadata=metadata,
            raw_markdown=markdown
        )

        return chapter

    def _extract_metadata(self, markdown: str) -> ChapterMetadata:

        chapter_match = re.search(
            r"Chapter\s+(\d+)\s*-\s*([^\n<]+)",
            markdown,
            flags=re.IGNORECASE,
        )

        if chapter_match:
            chapter_number = int(chapter_match.group(1))
            title = chapter_match.group(2).strip()
        else:
            chapter_number = 0
            title = "Unknown"

        class_match = re.search(
            r"Class\s+(\d+)",
            markdown,
            flags=re.IGNORECASE,
        )

        grade = class_match.group(1) if class_match else "Unknown"

        slug = (
            title.lower()
            .replace(" ", "-")
            .replace("&", "and")
        )

        curriculum_id = f"jee-main-2026-mathematics"

        return ChapterMetadata(
            chapter_id=f"chapter-{chapter_number:03d}",
            curriculum_id=curriculum_id,
            order=chapter_number,
            title=title,
            slug=slug,
            exam="JEE Main",
            subject="Mathematics",
            grade=grade,
            version="2026",
            summary="",
        )