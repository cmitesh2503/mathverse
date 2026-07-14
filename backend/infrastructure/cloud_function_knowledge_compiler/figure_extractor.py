from __future__ import annotations

import html
import re
from typing import Optional

from models import (
    ExtractionResult,
    Figure,
)


class FigureExtractor:

    """
    Deterministically extracts figure, diagram, and image references.
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
        chapter,
        document_text: Optional[str] = None,
        next_chapter=None,
    ):
        """
        Populate chapter.figures.

        The one-argument ExtractionResult return is retained for old direct
        callers that expected the previous stub shape.
        """

        if document_text is None:
            return ExtractionResult(
                success=True,
                document_type="figures",
                metadata={},
                data={
                    "figures": []
                },
            )

        chapter_text = self._chapter_text(
            chapter,
            document_text,
            next_chapter,
        )

        figures = []
        seen = set()

        for candidate in self._figure_candidates(chapter_text):
            key = self._figure_key(candidate)

            if key in seen:
                continue

            seen.add(key)

            order = len(figures) + 1
            image_ref = candidate["image_ref"]

            figure = Figure(
                id=self._figure_id(
                    chapter,
                    order,
                ),
                chapter_id=chapter.id,
                order=order,
                reference=candidate["reference"],
                caption=candidate["caption"],
                image_ref=image_ref,
                image_path=image_ref,
                description=candidate["description"],
                figure_type=candidate["figure_type"],
                concept_ids=self._concept_ids(
                    chapter,
                    candidate,
                ),
            )

            figures.append(figure)

        chapter.figures = figures

        return chapter

    def _chapter_text(
        self,
        chapter,
        document_text: str,
        next_chapter=None,
    ) -> str:

        start = self._find_heading_offset(
            document_text,
            chapter.name,
        )

        if start is None:
            return document_text

        end = len(document_text)

        if next_chapter is not None:
            next_start = self._find_heading_offset(
                document_text,
                next_chapter.name,
                start + 1,
            )

            if next_start is not None:
                end = next_start

        return document_text[start:end]

    def _find_heading_offset(
        self,
        text: str,
        title: str,
        start_at: int = 0,
    ) -> Optional[int]:

        title_key = self._normalize_heading(title)

        if not title_key:
            return None

        offset = 0

        for line in text.splitlines(keepends=True):
            next_offset = offset + len(line)

            if next_offset <= start_at:
                offset = next_offset
                continue

            line_key = self._normalize_heading(line)

            if line_key == title_key:
                return offset

            if title_key in line_key and len(line_key) <= len(title_key) + 24:
                return offset

            offset = next_offset

        return None

    def _figure_candidates(
        self,
        content: str,
    ) -> list[dict[str, str]]:

        candidates = []
        occupied_spans = []

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

    def _concept_ids(
        self,
        chapter,
        candidate: dict[str, str],
    ) -> list[str]:

        text = (
            f"{candidate['reference']} "
            f"{candidate['caption']} "
            f"{candidate['description']}"
        ).casefold()
        concept_ids = []

        for concept in getattr(chapter, "concepts", []):
            name = getattr(concept, "name", "")

            if not name:
                continue

            if name.casefold() in text:
                concept_ids.append(concept.id)

        return concept_ids

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

    def _figure_id(
        self,
        chapter,
        index: int,
    ) -> str:

        chapter_id = self._document_id(
            getattr(chapter, "id", "") or getattr(chapter, "name", "")
        )

        return f"{chapter_id}_figure_{index:03d}"

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

    def _html_attrs(
        self,
        raw_attrs: str,
    ) -> dict[str, str]:

        attrs = {}

        for match in self._HTML_ATTR_PATTERN.finditer(raw_attrs):
            value = (
                match.group("double")
                or match.group("single")
                or match.group("bare")
                or ""
            )

            attrs[match.group("name").lower()] = html.unescape(value)

        return attrs

    def _strip_section_number(
        self,
        text: str,
    ) -> str:

        return re.sub(
            r"^(?:chapter\s+)?\d+(?:\.\d+)*[.)]?\s+",
            "",
            text.strip(),
            flags=re.IGNORECASE,
        )

    def _normalize_heading(
        self,
        text: str,
    ) -> str:

        text = re.sub(
            r"^#+\s+",
            "",
            text.strip(),
        )

        text = self._strip_section_number(text)

        text = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.lower(),
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    def _document_id(
        self,
        text: str,
    ) -> str:

        document_id = re.sub(
            r"[^a-z0-9]+",
            "_",
            str(text or "").lower(),
        ).strip("_")

        return document_id or "figure"

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
