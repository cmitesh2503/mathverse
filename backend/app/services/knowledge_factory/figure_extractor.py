"""
MathVerse Knowledge Factory

Figure Extractor

Deterministically extracts figure and diagram references from parsed sections.

No AI.
No Firestore.
Consumes SectionParser and ConceptExtractor output.
"""

from __future__ import annotations

import html
import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Figure,
)
from app.services.knowledge_factory.section_content import (
    local_section_content,
)


class FigureExtractor:
    """
    Builds Figure objects from Azure markdown and textual figure references.
    """

    _FIGURE_BLOCK_PATTERN = re.compile(
        r"<figure\b[^>]*>(?P<body>.*?)</figure>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    _FIGCAPTION_PATTERN = re.compile(
        r"<figcaption\b[^>]*>(?P<body>.*?)</figcaption>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    _MARKDOWN_IMAGE_PATTERN = re.compile(
        r"!\[(?P<alt>[^\]]*)\]\("
        r"(?P<target>[^)\s]+)"
        r"(?:\s+\"(?P<title>[^\"]+)\")?"
        r"\)"
    )

    _HTML_IMAGE_PATTERN = re.compile(
        r"<img\b(?P<attrs>[^>]*)>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    _HTML_ATTR_PATTERN = re.compile(
        r"(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*"
        r"(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'|(?P<bare>[^\s\"'=<>`]+))"
    )

    _REFERENCE_PATTERN = re.compile(
        r"\b(?P<label>fig(?:ure)?|diagram|image)\.?\s*"
        r"(?P<number>\d+(?:\.\d+)*(?:\s*\([^)]+\))?)",
        flags=re.IGNORECASE,
    )

    _HTML_TAG_PATTERN = re.compile(
        r"<[^>]+>"
    )

    _HTML_COMMENT_PATTERN = re.compile(
        r"<!--.*?-->",
        flags=re.DOTALL,
    )

    def extract(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        figures: list[Figure] = []
        seen: set[str] = set()

        sections_by_id = {
            section.section_id: section
            for section in chapter.sections
        }

        for section in chapter.sections:
            section.figure_ids = []

        for section in chapter.sections:
            content = local_section_content(
                section,
                sections_by_id,
            )

            for candidate in self._figure_candidates(content):
                key = self._figure_key(candidate)

                if key in seen:
                    continue

                seen.add(key)

                figure_id = self._figure_id(
                    section.section_id,
                    len(section.figure_ids) + 1,
                )

                image_ref = candidate["image_ref"]

                figure = Figure(
                    figure_id=figure_id,
                    caption=candidate["caption"],
                    image_path=image_ref,
                    description=candidate["description"],
                    reference=candidate["reference"],
                    image_ref=image_ref,
                    figure_type=candidate["figure_type"],
                    section_id=section.section_id,
                    chapter_id=chapter.metadata.chapter_id,
                    curriculum_id=chapter.metadata.curriculum_id,
                    concept_ids=list(section.concept_ids),
                )

                figures.append(figure)
                section.figure_ids.append(figure.figure_id)

        chapter.figures = figures

        return chapter

    def _figure_candidates(
        self,
        content: str,
    ) -> list[dict[str, str]]:

        candidates: list[dict[str, str]] = []
        occupied_spans: list[tuple[int, int]] = []

        for match in self._FIGURE_BLOCK_PATTERN.finditer(content):
            candidate = self._figure_block_candidate(match)

            if candidate:
                candidates.append(candidate)
                occupied_spans.append(
                    (
                        int(candidate["start"]),
                        int(candidate["end"]),
                    )
                )

        for match in self._MARKDOWN_IMAGE_PATTERN.finditer(content):
            if self._inside_any_span(match.start(), occupied_spans):
                continue

            candidate = self._markdown_image_candidate(
                content,
                match,
            )

            if candidate:
                candidates.append(candidate)
                occupied_spans.append(
                    (
                        int(candidate["start"]),
                        int(candidate["end"]),
                    )
                )

        for match in self._HTML_IMAGE_PATTERN.finditer(content):
            if self._inside_any_span(match.start(), occupied_spans):
                continue

            candidate = self._html_image_candidate(
                content,
                match,
            )

            if candidate:
                candidates.append(candidate)
                occupied_spans.append(
                    (
                        int(candidate["start"]),
                        int(candidate["end"]),
                    )
                )

        for match in self._REFERENCE_PATTERN.finditer(content):
            if self._inside_any_span(match.start(), occupied_spans):
                continue

            candidates.append(
                self._reference_candidate(
                    content,
                    match,
                )
            )

        return sorted(
            candidates,
            key=lambda candidate: int(candidate["start"]),
        )

    def _figure_block_candidate(
        self,
        match: re.Match[str],
    ) -> dict[str, str] | None:

        body = match.group("body")
        image_ref = self._first_image_ref(body)
        caption = self._figcaption(body)

        if not caption:
            caption = self._first_image_caption(body)

        if not caption:
            caption = self._first_reference_text(body)

        description = self._clean_text(body)

        if not caption:
            caption = self._short_caption(description)

        reference = self._first_reference_text(
            f"{caption}\n{description}"
        )

        if not any([caption, image_ref, reference]):
            return None

        return self._candidate(
            start=match.start(),
            end=match.end(),
            reference=reference,
            caption=caption or reference,
            image_ref=image_ref,
            description=description,
        )

    def _markdown_image_candidate(
        self,
        content: str,
        match: re.Match[str],
    ) -> dict[str, str] | None:

        image_ref = self._clean_ref(match.group("target"))

        if not image_ref:
            return None

        alt = self._clean_text(match.group("alt"))
        title = self._clean_text(match.group("title") or "")
        caption = title or alt
        context = self._nearby_context(
            content,
            match.start(),
            match.end(),
        )
        reference = self._first_reference_text(
            f"{caption}\n{context}"
        )

        return self._candidate(
            start=match.start(),
            end=match.end(),
            reference=reference,
            caption=caption or reference or image_ref,
            image_ref=image_ref,
            description=context,
        )

    def _html_image_candidate(
        self,
        content: str,
        match: re.Match[str],
    ) -> dict[str, str] | None:

        attrs = self._html_attrs(match.group("attrs"))
        image_ref = self._clean_ref(attrs.get("src", ""))

        if not image_ref:
            return None

        caption = self._clean_text(
            attrs.get("title", "") or attrs.get("alt", "")
        )
        context = self._nearby_context(
            content,
            match.start(),
            match.end(),
        )
        reference = self._first_reference_text(
            f"{caption}\n{context}"
        )

        return self._candidate(
            start=match.start(),
            end=match.end(),
            reference=reference,
            caption=caption or reference or image_ref,
            image_ref=image_ref,
            description=context,
        )

    def _reference_candidate(
        self,
        content: str,
        match: re.Match[str],
    ) -> dict[str, str]:

        reference = self._normalize_reference_match(match)
        line = self._line_at(
            content,
            match.start(),
        )
        context = self._nearby_context(
            content,
            match.start(),
            match.end(),
        )

        if self._reference_only_line(line):
            caption = reference
        elif len(line) <= 120 and line.casefold().startswith(
            reference.casefold()
        ):
            caption = line.rstrip(" .")
        else:
            caption = reference

        return self._candidate(
            start=match.start(),
            end=match.end(),
            reference=reference,
            caption=caption,
            image_ref="",
            description=context if context != caption else "",
        )

    def _candidate(
        self,
        start: int,
        end: int,
        reference: str,
        caption: str,
        image_ref: str,
        description: str,
    ) -> dict[str, str]:

        text = f"{reference} {caption} {image_ref} {description}"

        return {
            "start": str(start),
            "end": str(end),
            "reference": reference.strip(),
            "caption": caption.strip(),
            "image_ref": image_ref.strip(),
            "description": self._truncate(description.strip(), 700),
            "figure_type": self._figure_type(text),
        }

    def _figcaption(
        self,
        body: str,
    ) -> str:

        match = self._FIGCAPTION_PATTERN.search(body)

        if match is None:
            return ""

        return self._clean_text(match.group("body"))

    def _first_image_ref(
        self,
        body: str,
    ) -> str:

        markdown = self._MARKDOWN_IMAGE_PATTERN.search(body)

        if markdown is not None:
            return self._clean_ref(markdown.group("target"))

        html_image = self._HTML_IMAGE_PATTERN.search(body)

        if html_image is None:
            return ""

        return self._clean_ref(
            self._html_attrs(html_image.group("attrs")).get("src", "")
        )

    def _first_image_caption(
        self,
        body: str,
    ) -> str:

        markdown = self._MARKDOWN_IMAGE_PATTERN.search(body)

        if markdown is not None:
            title = self._clean_text(markdown.group("title") or "")
            alt = self._clean_text(markdown.group("alt"))

            return title or alt

        html_image = self._HTML_IMAGE_PATTERN.search(body)

        if html_image is None:
            return ""

        attrs = self._html_attrs(html_image.group("attrs"))

        return self._clean_text(
            attrs.get("title", "") or attrs.get("alt", "")
        )

    def _first_reference_text(
        self,
        text: str,
    ) -> str:

        match = self._REFERENCE_PATTERN.search(text)

        if match is None:
            return ""

        return self._normalize_reference_match(match)

    def _normalize_reference_match(
        self,
        match: re.Match[str],
    ) -> str:

        label = match.group("label").lower().rstrip(".")
        number = re.sub(
            r"\s+",
            " ",
            match.group("number"),
        ).strip()

        if label == "diagram":
            prefix = "Diagram"
        elif label == "image":
            prefix = "Image"
        elif label == "figure":
            prefix = "Figure"
        else:
            prefix = "Fig."

        return f"{prefix} {number}"

    def _nearby_context(
        self,
        content: str,
        start: int,
        end: int,
    ) -> str:

        line = self._line_at(
            content,
            start,
        )

        if len(line) <= 240:
            return line

        window_start = max(0, start - 120)
        window_end = min(len(content), end + 120)

        return self._clean_text(
            content[window_start:window_end]
        )

    def _line_at(
        self,
        content: str,
        offset: int,
    ) -> str:

        line_start = content.rfind("\n", 0, offset) + 1
        line_end = content.find("\n", offset)

        if line_end == -1:
            line_end = len(content)

        return self._clean_text(
            content[line_start:line_end]
        )

    def _reference_only_line(
        self,
        line: str,
    ) -> bool:

        without_refs = self._REFERENCE_PATTERN.sub(
            "",
            line,
        )

        return not without_refs.strip(" .,:;()[]")

    def _figure_type(
        self,
        text: str,
    ) -> str:

        normalized = text.casefold()

        if "diagram" in normalized:
            return "diagram"

        if re.search(
            r"\b(triangle|circle|graph|axis|axes|line segment|angle|"
            r"quadrilateral|polygon|coordinate|construction)\b",
            normalized,
        ):
            return "diagram"

        if any(
            marker in normalized
            for marker in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
        ):
            return "image"

        return "figure"

    def _figure_key(
        self,
        candidate: dict[str, str],
    ) -> str:

        reference = candidate["reference"]

        if reference:
            return "ref:" + self._normalize_key(reference)

        image_ref = candidate["image_ref"]

        if image_ref:
            return "image:" + self._normalize_key(image_ref)

        return "caption:" + self._normalize_key(candidate["caption"])

    def _figure_id(
        self,
        section_id: str,
        index: int,
    ) -> str:

        return f"{section_id}-figure-{index:03d}"

    def _html_attrs(
        self,
        raw_attrs: str,
    ) -> dict[str, str]:

        attrs: dict[str, str] = {}

        for match in self._HTML_ATTR_PATTERN.finditer(raw_attrs):
            value = (
                match.group("double")
                or match.group("single")
                or match.group("bare")
                or ""
            )

            attrs[match.group("name").lower()] = html.unescape(value)

        return attrs

    def _clean_ref(
        self,
        value: str,
    ) -> str:

        return html.unescape(str(value or "")).strip().strip("\"'")

    def _clean_text(
        self,
        text: str,
    ) -> str:

        cleaned = html.unescape(str(text or ""))

        cleaned = self._HTML_COMMENT_PATTERN.sub(
            " ",
            cleaned,
        )

        cleaned = self._MARKDOWN_IMAGE_PATTERN.sub(
            lambda match: match.group("title") or match.group("alt") or " ",
            cleaned,
        )

        cleaned = re.sub(
            r"`([^`]+)`",
            r"\1",
            cleaned,
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

        cleaned = self._HTML_TAG_PATTERN.sub(
            " ",
            cleaned,
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        )

        return cleaned.strip()

    def _short_caption(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        first_sentence = re.split(
            r"(?<=[.!?])\s+",
            text,
            maxsplit=1,
        )[0]

        return self._truncate(
            first_sentence,
            160,
        )

    def _truncate(
        self,
        text: str,
        limit: int,
    ) -> str:

        if len(text) <= limit:
            return text

        return text[: limit - 3].rstrip() + "..."

    def _inside_any_span(
        self,
        offset: int,
        spans: list[tuple[int, int]],
    ) -> bool:

        return any(
            start <= offset < end
            for start, end in spans
        )

    def _normalize_key(
        self,
        text: str,
    ) -> str:

        return re.sub(
            r"\s+",
            "",
            str(text or "").casefold(),
        )
