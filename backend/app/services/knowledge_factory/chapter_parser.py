"""
MathVerse Knowledge Factory

Chapter Parser

Converts Azure Document Intelligence Layout JSON
into ChapterKnowledge.

Responsibilities
----------------
1. Load Azure Layout JSON
2. Extract markdown
3. Parse chapter metadata
4. Return ChapterKnowledge

Specialized extractors populate:

- Concepts
- Formulas
- Examples
- Exercises
- Figures
- Embeddings
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
    """
    Parses Azure Document Intelligence Layout output
    into a ChapterKnowledge object.
    """

    def parse(self, json_path: str | Path) -> ChapterKnowledge:

        json_path = Path(json_path)

        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        analyze_result = data.get("analyzeResult", {})

        markdown = analyze_result.get("content", "")

        metadata = self._extract_metadata(markdown)

        return ChapterKnowledge(
            metadata=metadata,
            raw_markdown=markdown,
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _extract_metadata(self, markdown: str) -> ChapterMetadata:

        chapter_number = self._extract_chapter_number(markdown)

        title = self._extract_chapter_title(markdown)

        grade = self._extract_grade(markdown)

        slug = self._slugify(title)

        curriculum_id = "jee-main-2026-mathematics"

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

    # ------------------------------------------------------------------
    # Chapter Number
    # ------------------------------------------------------------------

    def _extract_chapter_number(self, markdown: str) -> int:
        """
        Supports Azure Layout PageHeader:

            <!-- PageHeader="Chapter 3" -->

        and legacy format:

            Chapter 3 - Matrices
        """

        match = re.search(
            r'PageHeader="Chapter\s+(\d+)"',
            markdown,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        match = re.search(
            r"Chapter\s+(\d+)\s*-\s*([^\n<]+)",
            markdown,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        return 0

    # ------------------------------------------------------------------
    # Chapter Title
    # ------------------------------------------------------------------

    def _extract_chapter_title(self, markdown: str) -> str:
        """
        Uses the first H1 heading.

        Example

            # MATRICES

        Falls back to:

            Chapter 3 - Matrices
        """

        match = re.search(
            r"^#\s+(.+)$",
            markdown,
            flags=re.MULTILINE,
        )

        if match:

            title = match.group(1).strip()

            title = re.sub(r"\s+", " ", title)

            return title.title()

        match = re.search(
            r"Chapter\s+\d+\s*-\s*([^\n<]+)",
            markdown,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip().title()

        return "Unknown"

    # ------------------------------------------------------------------
    # Grade
    # ------------------------------------------------------------------

    def _extract_grade(self, markdown: str) -> str:

        match = re.search(
            r'PageHeader="Class\s+(\d+)"',
            markdown,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        match = re.search(
            r"Class\s+(\d+)",
            markdown,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return "Unknown"

    # ------------------------------------------------------------------
    # Slug
    # ------------------------------------------------------------------

    def _slugify(self, text: str) -> str:

        slug = text.lower()

        slug = slug.replace("&", "and")

        slug = re.sub(r"[^a-z0-9]+", "-", slug)

        slug = slug.strip("-")

        return slug