"""
MathVerse Knowledge Factory

Section Parser

Splits Azure Document Intelligence markdown into
structured sections.

Responsibilities
----------------
1. Parse markdown headings
2. Preserve hierarchy
3. Preserve section content

No AI.
No Firestore.
Pure deterministic parsing.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Section,
)


class SectionParser:
    """
    Converts chapter markdown into structured sections.
    """

    _heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+)$",
        flags=re.MULTILINE,
    )

    _number_pattern = re.compile(
        r"^(\d+(?:\.\d+)*)\s+(.*)$"
    )

    def parse(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        markdown = chapter.raw_markdown

        matches = list(self._heading_pattern.finditer(markdown))

        if not matches:
            return chapter

        sections: list[Section] = []

        for index, match in enumerate(matches):

            level = len(match.group(1))

            heading = match.group(2).strip()

            content_start = match.end()

            if index + 1 < len(matches):
                content_end = matches[index + 1].start()
            else:
                content_end = len(markdown)

            content = markdown[
                content_start:content_end
            ].strip()

            number = ""

            title = heading

            numbered = self._number_pattern.match(heading)

            if numbered:
                number = numbered.group(1)
                title = numbered.group(2).strip()

            section = Section(
                section_id=self._slug(title),
                number=number,
                title=title,
                level=level,
                content=content,
            )

            sections.append(section)

        chapter.sections = sections

        return chapter

    @staticmethod
    def _slug(text: str) -> str:

        slug = text.lower()

        slug = slug.replace("&", "and")

        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            slug,
        )

        return slug.strip("-")