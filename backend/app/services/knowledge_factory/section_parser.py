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
        r"^(#{1,6})\s+(.+)$"
    )

    _number_pattern = re.compile(
        r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.+)$"
    )

    def parse(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        markdown = chapter.raw_markdown

        markers = self._find_section_markers(markdown)

        if not markers:
            return chapter

        sections: list[Section] = []

        for index, marker in enumerate(markers):

            content_start = marker["end"]

            if index + 1 < len(markers):
                content_end = markers[index + 1]["start"]
            else:
                content_end = len(markdown)

            content = markdown[
                content_start:content_end
            ].strip()

            section = Section(
                section_id=self._section_id(
                    marker["number"],
                    marker["title"],
                ),
                number=marker["number"],
                title=marker["title"],
                level=marker["level"],
                content=content,
            )

            sections.append(section)

        chapter.sections = sections

        return chapter

    def _find_section_markers(
        self,
        markdown: str,
    ) -> list[dict[str, int | str]]:

        markers: list[dict[str, int | str]] = []

        offset = 0

        for line in markdown.splitlines(keepends=True):

            line_without_newline = line.rstrip("\r\n")

            parsed = self._parse_marker(line_without_newline)

            if parsed is not None:
                markers.append(
                    {
                        "start": offset,
                        "end": offset + len(line),
                        "level": parsed["level"],
                        "number": parsed["number"],
                        "title": parsed["title"],
                    }
                )

            offset += len(line)

        return markers

    def _parse_marker(
        self,
        line: str,
    ) -> dict[str, int | str] | None:

        stripped = line.strip()

        if not stripped:
            return None

        heading = self._heading_pattern.match(stripped)

        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            number, title = self._split_number(title)

            return {
                "level": level,
                "number": number,
                "title": title,
            }

        number, title = self._split_number(stripped)

        if not number or not self._looks_like_section_title(title):
            return None

        if "." not in number and not self._looks_like_top_level_title(title):
            return None

        return {
            "level": number.count(".") + 1,
            "number": number,
            "title": title,
        }

    def _split_number(
        self,
        title: str,
    ) -> tuple[str, str]:

        numbered = self._number_pattern.match(title)

        if not numbered:
            return "", title.strip()

        return (
            numbered.group(1),
            numbered.group(2).strip(),
        )

    def _looks_like_section_title(
        self,
        title: str,
    ) -> bool:

        if len(title) > 120:
            return False

        if not re.search(r"[A-Za-z]", title):
            return False

        if re.search(r"[=<>]|\\frac|\\int|\\sum", title):
            return False

        return len(title.split()) <= 14

    def _looks_like_top_level_title(
        self,
        title: str,
    ) -> bool:

        words = re.findall(
            r"[A-Za-z]+",
            title,
        )

        if len(words) <= 2:
            return True

        title_words = [
            word
            for word in words
            if word[:1].isupper()
        ]

        return len(title_words) / len(words) >= 0.5

    def _section_id(
        self,
        number: str,
        title: str,
    ) -> str:

        if number:
            return self._slug(f"{number}-{title}")

        return self._slug(title)

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
