"""
MathVerse Knowledge Factory

Example Extractor

Deterministically extracts worked examples from parsed sections.

No AI.
No Firestore.
Consumes SectionParser and ConceptExtractor output.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Example,
)
from app.services.knowledge_factory.section_content import (
    local_section_content,
)


class ExampleExtractor:
    """
    Builds Example objects from parsed chapter sections.
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
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        examples: list[Example] = []
        seen: set[str] = set()

        concepts_by_section = self._concept_ids_by_section(chapter)
        concepts_by_id = {
            concept.concept_id: concept
            for concept in chapter.concepts
        }
        sections_by_id = {
            section.section_id: section
            for section in chapter.sections
        }

        for section in chapter.sections:
            section.example_ids = []

        for concept in chapter.concepts:
            concept.examples = []

        for section in chapter.sections:
            if self._SKIPPED_SECTION_PATTERN.match(section.title.strip()):
                continue

            concept_ids = (
                section.concept_ids
                or concepts_by_section.get(section.section_id, [])
            )

            if not concept_ids:
                continue

            content = local_section_content(
                section,
                sections_by_id,
            )

            for title, body_lines in self._example_blocks(content):
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

                example_id = self._example_id(
                    section.section_id,
                    len(section.example_ids) + 1,
                )

                example = Example(
                    example_id=example_id,
                    title=title,
                    problem=problem,
                    solution=solution,
                    difficulty=self._difficulty(
                        problem,
                        solution,
                    ),
                    concept_ids=list(concept_ids),
                    section_id=section.section_id,
                )

                examples.append(example)
                section.example_ids.append(example.example_id)

                for concept_id in concept_ids:
                    concept = concepts_by_id.get(concept_id)

                    if concept is None:
                        continue

                    if example.example_id not in concept.examples:
                        concept.examples.append(example.example_id)

        chapter.examples = examples

        return chapter

    def _example_blocks(
        self,
        content: str,
    ) -> list[tuple[str, list[str]]]:

        blocks: list[tuple[str, list[str]]] = []
        lines = content.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            heading = self._EXAMPLE_HEADING_PATTERN.match(line)

            if heading is None:
                index += 1
                continue

            title = self._example_title(heading)
            body_lines: list[str] = []
            tail = heading.group("tail").strip()

            if tail:
                body_lines.append(tail)

            index += 1

            while index < len(lines):
                next_line = lines[index]
                stripped = next_line.strip()

                if (
                    stripped
                    and self._EXAMPLE_HEADING_PATTERN.match(stripped)
                ):
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

        problem_lines: list[str] = []
        solution_lines: list[str] = []
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

    def _concept_ids_by_section(
        self,
        chapter: ChapterKnowledge,
    ) -> dict[str, list[str]]:

        concept_ids: dict[str, list[str]] = {}

        for concept in chapter.concepts:
            if not concept.section_id:
                continue

            concept_ids.setdefault(
                concept.section_id,
                [],
            ).append(concept.concept_id)

        return concept_ids

    def _example_id(
        self,
        section_id: str,
        index: int,
    ) -> str:

        return f"{section_id}-example-{index:03d}"

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
