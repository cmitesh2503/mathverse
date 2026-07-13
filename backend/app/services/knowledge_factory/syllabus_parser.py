from __future__ import annotations

import html
import re
from pathlib import PurePosixPath
from typing import Any

from app.services.knowledge_factory.syllabus_models import (
    Syllabus,
    SyllabusChapter,
    SyllabusTopic,
)


class SyllabusParser:
    """
    Deterministically parses Azure Layout markdown into syllabus structure.

    The parser accepts either:
    - raw merged markdown from SyllabusPipeline
    - Azure Layout JSON/dict with a top-level or analyzeResult content field
    """

    _UNIT_PATTERN = re.compile(
        "^(?:unit|chapter|ch\\.?)\\s*[-:\\u2010-\\u2015]?\\s*"
        "([ivxlcdm]+|\\d{1,2})\\s*[:.)|\\-\\u2010-\\u2015]?\\s*(.+)$",
        re.IGNORECASE,
    )
    _UNIT_LABEL_PATTERN = re.compile(
        "^(?:unit|chapter|ch\\.?)\\s*[-:\\u2010-\\u2015]?\\s*"
        "([ivxlcdm]+|\\d{1,2})\\s*[.)]?\\s*$",
        re.IGNORECASE,
    )
    _NUMBERED_PATTERN = re.compile(r"^(\d{1,2})\s*[.)-]\s+(.+)$")
    _GRADE_PATTERN = re.compile(r"\b(?:class|grade)\s*[-:]?\s*(\d{1,2}|ix|x|xi|xii)\b", re.IGNORECASE)
    _VERSION_PATTERN = re.compile(r"\b(20\d{2}(?:-\d{2})?)\b")
    _TAG_PATTERN = re.compile(r"<[^>]+>")
    _COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
    _TABLE_ROW_PATTERN = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    _TABLE_CELL_PATTERN = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
    _SUBJECT_HEADING_PATTERN = re.compile(
        r"^(?:(?:part|section)\s+[a-z0-9ivxlcdm]+\s*[-:]\s*)?"
        r"(?:subject\s*[-:]?\s*)?"
        r"(mathematics|maths|physics|chemistry)"
        r"(?:\s*\([^)]*\))?\s*:?$",
        re.IGNORECASE,
    )

    _SKIP_LINE_PREFIXES = (
        "marks",
        "periods",
        "total",
        "unit no",
        "unit number",
        "chapter no",
        "chapter number",
        "name of unit",
        "name of chapter",
        "deleted",
        "rationale",
        "course structure",
        "time:",
        "max marks",
        "general instructions",
        "internal assessment",
    )

    _ROMAN_VALUES = {
        "i": 1,
        "ii": 2,
        "iii": 3,
        "iv": 4,
        "v": 5,
        "vi": 6,
        "vii": 7,
        "viii": 8,
        "ix": 9,
        "x": 10,
        "xi": 11,
        "xii": 12,
    }

    def parse(
        self,
        document: str | dict[str, Any],
        *,
        source_path: str = "",
        board: str | None = None,
        grade: str | None = None,
        subject: str | None = None,
        version: str | None = None,
    ) -> Syllabus:
        markdown = self._content_from_document(document)
        if not markdown.strip():
            raise ValueError("Syllabus content is empty.")

        path_metadata = self._metadata_from_source_path(source_path)
        resolved_board = self._normalize_board(board or path_metadata.get("board") or self._extract_board(markdown))
        resolved_grade = self._normalize_grade(grade or path_metadata.get("grade") or self._extract_grade(markdown))
        if not resolved_grade and resolved_board == "jee":
            resolved_grade = "jee-main"
        resolved_subject = subject or self._extract_subject(markdown)
        resolved_version = version or self._extract_version(markdown)

        subject_markdown = self._markdown_for_subject(
            markdown,
            resolved_subject,
        )

        chapters = self._extract_chapters(subject_markdown)
        syllabus_id = f"{resolved_board}_{resolved_grade}_{self._slug(resolved_subject)}"

        return Syllabus(
            syllabus_id=syllabus_id,
            board=resolved_board,
            grade=resolved_grade,
            subject=resolved_subject,
            version=resolved_version,
            source_path=source_path,
            chapters=chapters,
        )

    def parse_markdown(
        self,
        markdown: str,
        *,
        source_path: str = "",
        board: str | None = None,
        grade: str | None = None,
        subject: str | None = None,
        version: str | None = None,
    ) -> Syllabus:
        return self.parse(
            markdown,
            source_path=source_path,
            board=board,
            grade=grade,
            subject=subject,
            version=version,
        )

    def _content_from_document(self, document: str | dict[str, Any]) -> str:
        return self.content_from_document(document)

    def content_from_document(self, document: str | dict[str, Any]) -> str:
        if isinstance(document, str):
            return document

        content = document.get("content")
        if isinstance(content, str):
            return content

        analyze_result = document.get("analyzeResult")
        if isinstance(analyze_result, dict):
            content = analyze_result.get("content")
            if isinstance(content, str):
                return content

        return ""

    def _metadata_from_source_path(self, source_path: str) -> dict[str, str]:
        if not source_path:
            return {}

        normalized = source_path.replace("\\", "/").strip("/")
        parts = [part for part in PurePosixPath(normalized).parts if part]
        metadata: dict[str, str] = {}

        board = ""
        if len(parts) >= 2 and parts[0].lower() == "syllabus":
            board = self._board_from_path_part(parts[1])
            if board:
                metadata["board"] = board

        if len(parts) >= 3 and board:
            grade_parts = parts[2:]
        elif len(parts) >= 2 and parts[0].lower() == "syllabus":
            grade_parts = parts[1:]
        else:
            grade_parts = parts

        for part in grade_parts:
            grade = self._normalize_grade(part)
            if grade:
                metadata["grade"] = grade
                break

        return metadata

    def _extract_board(self, markdown: str) -> str:
        lowered = markdown.lower()
        if "central board of secondary education" in lowered or "cbse" in lowered:
            return "cbse"
        if "joint entrance examination" in lowered or "jee" in lowered:
            return "jee"
        return "unknown"

    def _board_from_path_part(
        self,
        value: str,
    ) -> str:
        normalized = self._slug(PurePosixPath(value).stem)
        if normalized in {"cbse", "central-board-of-secondary-education"}:
            return "cbse"
        if normalized in {"jee", "jee-main", "jee-advanced"}:
            return "jee"
        return ""

    def _normalize_board(self, value: str | None) -> str:
        normalized = self._slug(value or "")
        if normalized in {"central-board-of-secondary-education"}:
            return "cbse"
        if normalized in {"jee-main", "jee-advanced"}:
            return "jee"
        return normalized or "unknown"

    def _extract_grade(self, markdown: str) -> str:
        match = self._GRADE_PATTERN.search(markdown)
        if match:
            return self._normalize_grade(match.group(1))

        lowered = markdown.lower()
        if "jee advanced" in lowered or "jee (advanced)" in lowered:
            return "jee-advanced"
        if (
            "jee main" in lowered
            or "jee (main)" in lowered
            or "joint entrance examination" in lowered
            or "b.e./b.tech" in lowered
            or "b.tech" in lowered
        ):
            return "jee-main"

        return ""

    def _normalize_grade(self, value: str | None) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return ""

        slug = self._slug(raw.replace(".pdf", ""))
        if slug in {"jee", "jee-main", "main", "joint-entrance-examination-main"}:
            return "jee-main"
        if slug in {"jee-advanced", "advanced", "joint-entrance-examination-advanced"}:
            return "jee-advanced"

        match = self._GRADE_PATTERN.search(raw)
        if match:
            raw = match.group(1)
        else:
            raw = raw.replace(".pdf", "")
            raw = raw.replace("class-", "").replace("class_", "").replace("class", "")
            raw = raw.replace("grade-", "").replace("grade_", "").replace("grade", "")

        raw = raw.strip("-_ .")
        if raw in self._ROMAN_VALUES:
            return f"grade-{self._ROMAN_VALUES[raw]:02d}"
        if raw.isdigit():
            return f"grade-{int(raw):02d}"
        return ""

    def _extract_subject(self, markdown: str) -> str:
        upper = markdown.upper()
        if "MATHEMATICS" in upper or "MATHS" in upper:
            return "Mathematics"
        if "PHYSICS" in upper:
            return "Physics"
        if "CHEMISTRY" in upper:
            return "Chemistry"
        return "Mathematics"

    def _extract_version(self, markdown: str) -> str:
        match = self._VERSION_PATTERN.search(markdown)
        return match.group(1) if match else "unknown"

    def _markdown_for_subject(
        self,
        markdown: str,
        subject: str,
    ) -> str:
        target_subject = self._canonical_subject(subject)
        if not target_subject:
            return markdown

        lines = markdown.splitlines(keepends=True)
        markers: list[tuple[int, str]] = []

        for index, line in enumerate(lines):
            marker_subject = self._subject_heading(line)
            if marker_subject:
                markers.append(
                    (index, marker_subject)
                )

        if not markers:
            return markdown

        for marker_index, (line_index, marker_subject) in enumerate(markers):
            if marker_subject != target_subject:
                continue

            next_line_index = len(lines)
            for next_index, (candidate_line_index, candidate_subject) in enumerate(markers[marker_index + 1 :], start=marker_index + 1):
                if candidate_subject != target_subject:
                    next_line_index = candidate_line_index
                    break

            return "".join(
                lines[line_index:next_line_index]
            )

        return markdown

    def _subject_heading(
        self,
        line: str,
    ) -> str:
        cleaned = self._clean_text(line)
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned)
        cleaned = cleaned.strip(" -*_")
        cleaned = re.sub(r"\s+", " ", cleaned)

        if "syllabus" in cleaned.lower() and len(cleaned.split()) > 3:
            return ""

        match = self._SUBJECT_HEADING_PATTERN.match(cleaned)
        if not match:
            return ""

        return self._canonical_subject(
            match.group(1)
        )

    def _canonical_subject(
        self,
        subject: str,
    ) -> str:
        normalized = self._slug(subject)
        if normalized in {"mathematics", "maths", "math"}:
            return "Mathematics"
        if normalized == "physics":
            return "Physics"
        if normalized == "chemistry":
            return "Chemistry"
        return ""

    def _extract_chapters(self, markdown: str) -> list[SyllabusChapter]:
        lines = self._normalized_lines(markdown)
        markers: list[tuple[int, int, int, str]] = []

        for index, line in enumerate(lines):
            marker = self._chapter_marker(line)
            content_start = index + 1
            if marker is None:
                marker = self._chapter_marker_with_following_title(
                    lines,
                    index,
                )
                if marker is not None:
                    content_start = index + 2

            if marker is None:
                continue
            order, title = marker
            if not self._is_valid_chapter_title(title):
                continue
            markers.append((index, content_start, order, title))

        chapters: list[SyllabusChapter] = []
        used_ids: set[str] = set()

        for marker_index, (line_index, content_start, order, title) in enumerate(markers):
            next_line_index = markers[marker_index + 1][0] if marker_index + 1 < len(markers) else len(lines)
            content_lines = lines[content_start:next_line_index]
            chapter_id = self._unique_id(f"chapter-{order:02d}", used_ids)
            chapters.append(
                SyllabusChapter(
                    chapter_id=chapter_id,
                    order=order,
                    title=title,
                    topics=self._extract_topics(content_lines),
                )
            )

        return chapters

    def _normalized_lines(self, markdown: str) -> list[str]:
        expanded = self._expand_table_rows(markdown)
        expanded = self._COMMENT_PATTERN.sub("\n", expanded)
        expanded = expanded.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        expanded = self._TAG_PATTERN.sub(" ", expanded)
        expanded = html.unescape(expanded)

        lines: list[str] = []
        for raw_line in expanded.splitlines():
            line = raw_line.strip()
            line = re.sub(r"^#{1,6}\s*", "", line)
            line = re.sub(r"^[*\-•]\s*", "", line)
            line = re.sub(r"\s+", " ", line).strip()
            line = line.strip("|").strip()
            if not line:
                continue
            if set(line) <= {"-", "=", "|", " "}:
                continue
            lines.append(line)
        return lines

    def _expand_table_rows(self, markdown: str) -> str:
        def replace_row(match: re.Match[str]) -> str:
            row = match.group(1)
            cells = [
                self._clean_text(self._TAG_PATTERN.sub(" ", cell))
                for cell in self._TABLE_CELL_PATTERN.findall(row)
            ]
            cells = [cell for cell in cells if cell]
            return "\n" + " | ".join(cells) + "\n" if cells else "\n"

        return self._TABLE_ROW_PATTERN.sub(replace_row, markdown)

    def _chapter_marker(self, line: str) -> tuple[int, str] | None:
        table_marker = self._chapter_marker_from_table_line(line)
        if table_marker is not None:
            return table_marker

        match = self._UNIT_PATTERN.match(line)
        if match:
            order = self._order_from_value(match.group(1))
            title = self._clean_chapter_title(match.group(2))
            if order is not None:
                return order, title

        match = self._NUMBERED_PATTERN.match(line)
        if match:
            title = self._clean_chapter_title(match.group(2))
            if self._looks_like_numbered_chapter(title):
                return int(match.group(1)), title

        return None

    def _chapter_marker_from_table_line(self, line: str) -> tuple[int, str] | None:
        if "|" not in line:
            return None

        cells = [self._clean_text(cell) for cell in line.split("|")]
        cells = [cell for cell in cells if cell]
        if len(cells) < 2:
            return None

        first = cells[0].lower()
        if first.startswith(
            (
                "unit no",
                "unit number",
                "chapter no",
                "chapter number",
                "s.no",
                "sl no",
            )
        ):
            return None

        order = self._order_from_value(cells[0])
        if order is None:
            return None

        for candidate in cells[1:]:
            title = self._clean_chapter_title(candidate)
            if self._is_valid_chapter_title(title):
                return order, title

        return None

    def _chapter_marker_with_following_title(
        self,
        lines: list[str],
        index: int,
    ) -> tuple[int, str] | None:
        if index + 1 >= len(lines):
            return None

        match = self._UNIT_LABEL_PATTERN.match(lines[index])
        if not match:
            return None

        order = self._order_from_value(match.group(1))
        if order is None:
            return None

        title = self._clean_chapter_title(lines[index + 1])
        if not self._is_valid_chapter_title(title):
            return None
        if self._chapter_marker(lines[index + 1]) is not None:
            return None

        return order, title

    def _order_from_value(self, value: str) -> int | None:
        normalized = str(value or "").strip().lower()
        normalized = re.sub(r"[\u2010-\u2015]", "-", normalized)
        label_match = re.match(
            r"^(?:unit|chapter|ch\.?)\s*-?\s*([ivxlcdm]+|\d{1,2})$",
            normalized,
        )
        if label_match:
            normalized = label_match.group(1)

        normalized = normalized.strip(".:-()")
        if normalized.isdigit():
            return int(normalized)
        return self._ROMAN_VALUES.get(normalized)

    def _clean_chapter_title(self, title: str) -> str:
        cleaned = self._clean_text(title)
        cleaned = re.sub(r"\b(?:marks?|periods?)\s*[:\-]?\s*\d+\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d+\s*(?:marks?|periods?)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip(" :-|")

    def _looks_like_numbered_chapter(self, title: str) -> bool:
        if not self._is_valid_chapter_title(title):
            return False
        words = title.split()
        if len(words) > 9:
            return False
        if title.endswith((".", ";", ",")):
            return False
        return True

    def _is_valid_chapter_title(self, title: str) -> bool:
        if not title or len(title) < 3 or len(title) > 120:
            return False
        lowered = title.lower()
        if lowered.startswith(self._SKIP_LINE_PREFIXES):
            return False
        if not re.search(r"[A-Za-z]", title):
            return False
        return True

    def _extract_topics(self, lines: list[str]) -> list[SyllabusTopic]:
        topics: list[SyllabusTopic] = []
        seen: set[str] = set()

        for line in lines:
            for candidate in self._topic_candidates(line):
                title, subtopics = self._topic_and_subtopics(candidate)
                if not title:
                    continue
                key = self._slug(title)
                if key in seen:
                    continue
                seen.add(key)
                topics.append(
                    SyllabusTopic(
                        topic_id=f"topic-{len(topics) + 1:03d}",
                        order=len(topics) + 1,
                        title=title,
                        subtopics=subtopics,
                    )
                )

        return topics

    def _topic_candidates(self, line: str) -> list[str]:
        cleaned = self._clean_text(line)
        if not cleaned:
            return []

        lowered = cleaned.lower()
        if lowered.startswith(self._SKIP_LINE_PREFIXES):
            return []
        if lowered.startswith(("unit ", "chapter ", "paper ", "section ")):
            return []
        if len(cleaned) < 4:
            return []

        parts = [part.strip() for part in re.split(r"\s*;\s*", cleaned) if part.strip()]
        if len(parts) > 1:
            return parts
        return [cleaned]

    def _topic_and_subtopics(self, text: str) -> tuple[str, list[str]]:
        text = self._clean_text(text)
        split = re.split(r"\s*[:\-]\s+", text, maxsplit=1)
        if len(split) == 2 and 3 <= len(split[0]) <= 80:
            title = split[0].strip()
            subtopics = self._split_subtopics(split[1])
            return title, subtopics

        return text.strip(" ."), []

    def _split_subtopics(self, text: str) -> list[str]:
        items = [self._clean_text(item).strip(" .") for item in re.split(r"\s*,\s*|\s*;\s*", text)]
        return [item for item in items if len(item) >= 2]

    def _unique_id(self, base: str, used_ids: set[str]) -> str:
        candidate = base
        suffix = 2
        while candidate in used_ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(candidate)
        return candidate

    def _clean_text(self, text: str) -> str:
        text = html.unescape(str(text or ""))
        text = self._COMMENT_PATTERN.sub(" ", text)
        text = self._TAG_PATTERN.sub(" ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _slug(self, text: str) -> str:
        slug = str(text or "").lower()
        slug = slug.replace("&", "and")
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")
