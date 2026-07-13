"""
Section content helpers for Knowledge Factory extractors.

SectionParser stores parent sections with child-section content included so the
full hierarchy is preserved. Extractors use these helpers when they need only the
section's own local content.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import Section


def local_section_content(
    section: Section,
    sections_by_id: dict[str, Section],
) -> str:
    content_end = len(section.content)

    for child_id in section.children:
        child = sections_by_id.get(child_id)

        if child is None:
            continue

        marker_start = _child_marker_start(
            section.content,
            child,
        )

        if marker_start is None:
            continue

        content_end = min(
            content_end,
            marker_start,
        )

    return section.content[:content_end].strip()


def _child_marker_start(
    content: str,
    child: Section,
) -> int | None:
    offset = 0

    for line in content.splitlines(keepends=True):
        if _matches_section_marker(
            line,
            child,
        ):
            return offset

        offset += len(line)

    return None


def _matches_section_marker(
    line: str,
    section: Section,
) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    heading = re.match(
        r"^#{1,6}\s+(.+)$",
        stripped,
    )

    if heading:
        stripped = heading.group(1).strip()

    candidates = {
        section.title,
    }

    if section.number:
        candidates.add(
            f"{section.number} {section.title}"
        )
        candidates.add(
            f"{section.number}. {section.title}"
        )

    marker = _normalize_marker_text(stripped)

    return any(
        marker == _normalize_marker_text(candidate)
        for candidate in candidates
    )


def _normalize_marker_text(text: str) -> str:
    normalized = _clean_inline_markdown(text)

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    normalized = normalized.strip().casefold()

    return normalized.rstrip(".")


def _clean_inline_markdown(text: str) -> str:
    cleaned = re.sub(
        r"`([^`]+)`",
        r"\1",
        str(text or ""),
    )

    cleaned = re.sub(
        r"\*\*([^*]+)\*\*",
        r"\1",
        cleaned,
    )

    cleaned = re.sub(
        r"__([^_]+)__",
        r"\1",
        cleaned,
    )

    cleaned = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        r"\1",
        cleaned,
    )

    cleaned = re.sub(
        r"(?<!_)_([^_]+)_(?!_)",
        r"\1",
        cleaned,
    )

    return cleaned.strip()
