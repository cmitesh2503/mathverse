from __future__ import annotations

import re
from typing import Optional

from models import (
    Example,
    ExtractionResult,
)


class ExampleExtractor:

    """
    Deterministically extracts worked examples from chapter text.
    """

    _EXAMPLE_HEADING_PATTERN = re.compile(
        r"^(?:#{1,6}\s*)?"
        r"(?P<label>(?:(?:solved|worked)\s+)?(?:example|illustration))\b"
        r"\s*(?P<number>\d+(?:\.\d+)*[A-Za-z]?)?"
        r"\s*(?:[:.-]\s*)?"
        r"(?P<tail>.*)$",
        flags=re.IGNORECASE,
    )

    _SOLUTION_PATTERN = re.compile(
        r"^(?:solution|sol\.?|answer)\s*:?\s*(?P<tail>.*)$",
        flags=re.IGNORECASE,
    )

    _PROBLEM_PREFIX_PATTERN = re.compile(
        r"^(?:problem|question)\s*:?\s*",
        flags=re.IGNORECASE,
    )

    _SKIPPED_SECTION_PATTERN = re.compile(
        r"^(exercise|exercises|miscellaneous exercise)\b",
        flags=re.IGNORECASE,
    )

    def extract(
        self,
        chapter,
        document_text: Optional[str] = None,
        next_chapter=None,
    ):
        """
        Populate chapter.examples.

        The one-argument ExtractionResult return is retained for old direct
        callers that expected the previous stub shape.
        """

        if document_text is None:
            return ExtractionResult(
                success=True,
                document_type="examples",
                metadata={},
                data={
                    "examples": []
                },
            )

        chapter_text = self._chapter_text(
            chapter,
            document_text,
            next_chapter,
        )

        chapter_text = self._remove_skipped_blocks(
            chapter_text,
        )

        examples = []
        seen = set()

        for title, body_lines in self._example_blocks(chapter_text):
            problem, solution = self._split_problem_solution(body_lines)

            if not problem or not solution:
                continue

            key = self._example_key(
                title,
                problem,
                solution,
            )

            if key in seen:
                continue

            seen.add(key)

            order = len(examples) + 1

            example = Example(
                id=self._example_id(
                    chapter,
                    order,
                ),
                chapter_id=chapter.id,
                order=order,
                title=title,
                problem=problem,
                solution=solution,
                difficulty=self._difficulty(
                    problem,
                    solution,
                ),
                concept_ids=self._concept_ids(
                    chapter,
                    title,
                    problem,
                    solution,
                ),
            )

            examples.append(example)

        chapter.examples = examples

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

    def _remove_skipped_blocks(
        self,
        text: str,
    ) -> str:

        kept = []
        skipping = False
        skip_level = 0

        for line in text.splitlines():
            heading = re.match(
                r"^\s*(#{1,6})\s+(.+)$",
                line,
            )

            stripped = line.strip()

            if heading:
                level = len(heading.group(1))
                title = self._strip_section_number(
                    heading.group(2).strip()
                )

                if skipping and level <= skip_level:
                    skipping = False

                if self._SKIPPED_SECTION_PATTERN.match(title):
                    skipping = True
                    skip_level = level
                    continue

            elif self._SKIPPED_SECTION_PATTERN.match(
                self._strip_section_number(stripped)
            ):
                skipping = True
                skip_level = 1
                continue

            if not skipping:
                kept.append(line)

        return "\n".join(kept)

    def _example_blocks(
        self,
        content: str,
    ) -> list[tuple[str, list[str]]]:

        blocks = []
        lines = content.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            heading = self._EXAMPLE_HEADING_PATTERN.match(line)

            if heading is None:
                index += 1
                continue

            title = self._example_title(heading)
            body_lines = []
            tail = heading.group("tail").strip()

            if tail:
                body_lines.append(tail)

            index += 1

            while index < len(lines):
                next_line = lines[index]
                stripped = next_line.strip()

                if stripped and self._EXAMPLE_HEADING_PATTERN.match(stripped):
                    break

                if stripped.startswith("#"):
                    break

                body_lines.append(next_line.rstrip())
                index += 1

            blocks.append(
                (
                    title,
                    body_lines,
                )
            )

        return blocks

    def _example_title(
        self,
        heading: re.Match[str],
    ) -> str:

        label = heading.group("label").strip().title()
        number = (heading.group("number") or "").strip()

        if number:
            return f"{label} {number}"

        return label

    def _split_problem_solution(
        self,
        body_lines: list[str],
    ) -> tuple[str, str]:

        problem_lines = []
        solution_lines = []
        in_solution = False

        for line in body_lines:
            cleaned = self._clean_line(line)

            if not cleaned:
                continue

            solution = self._SOLUTION_PATTERN.match(cleaned)

            if solution:
                in_solution = True
                tail = solution.group("tail").strip()

                if tail:
                    solution_lines.append(tail)

                continue

            if in_solution:
                solution_lines.append(cleaned)
                continue

            problem_lines.append(
                self._strip_problem_prefix(cleaned)
            )

        return (
            self._join_lines(problem_lines),
            self._join_lines(solution_lines),
        )

    def _difficulty(
        self,
        problem: str,
        solution: str,
    ) -> str:

        line_count = len(
            [
                line
                for line in solution.splitlines()
                if line.strip()
            ]
        )
        total_length = len(problem) + len(solution)

        if total_length > 1200 or line_count > 16:
            return "Hard"

        if total_length < 350 and line_count <= 5:
            return "Easy"

        return "Medium"

    def _concept_ids(
        self,
        chapter,
        title: str,
        problem: str,
        solution: str,
    ) -> list[str]:

        text = f"{title} {problem} {solution}".casefold()
        concept_ids = []

        for concept in getattr(chapter, "concepts", []):
            name = getattr(concept, "name", "")

            if not name:
                continue

            if name.casefold() in text:
                concept_ids.append(concept.id)

        return concept_ids

    def _example_id(
        self,
        chapter,
        index: int,
    ) -> str:

        chapter_id = self._document_id(
            getattr(chapter, "id", "") or getattr(chapter, "name", "")
        )

        return f"{chapter_id}_example_{index:03d}"

    def _example_key(
        self,
        title: str,
        problem: str,
        solution: str,
    ) -> str:

        return re.sub(
            r"\s+",
            "",
            f"{title}\n{problem}\n{solution}".casefold(),
        )

    def _strip_problem_prefix(
        self,
        text: str,
    ) -> str:

        return self._PROBLEM_PREFIX_PATTERN.sub(
            "",
            text,
        ).strip()

    def _clean_line(
        self,
        line: str,
    ) -> str:

        cleaned = line.strip()

        cleaned = re.sub(
            r"^\s*(?:[-*+]|\d+[.)])\s+",
            "",
            cleaned,
        )

        return self._clean_inline_markdown(cleaned)

    def _join_lines(
        self,
        lines: list[str],
    ) -> str:

        return "\n".join(
            line
            for line in lines
            if line.strip()
        ).strip()

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

        return document_id or "example"

    @staticmethod
    def _clean_inline_markdown(
        text: str,
    ) -> str:

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
