from __future__ import annotations

import re
from typing import Optional

from models import (
    Exercise,
    ExtractionResult,
)


class ExerciseExtractor:

    """
    Deterministically extracts chapter exercises and practice questions.
    """

    _BLOCK_HEADING_PATTERN = re.compile(
        r"^(?:#{1,6}\s*)?"
        r"(?P<label>exercise|practice|questions?|mcqs?|"
        r"multiple\s+choice\s+questions?|numericals?|numerical\s+problems?)\b"
        r"\s*(?P<number>\d+(?:\.\d+)*)?"
        r"\s*(?:[:.-]\s*)?"
        r"(?P<tail>.*)$",
        flags=re.IGNORECASE,
    )

    _QUESTION_MARKER_PATTERN = re.compile(
        r"(?m)^\s*(?:Q(?:uestion)?\.?\s*)?(?P<number>\d+)[.)]\s+"
    )

    _QUESTION_WORD_MARKER_PATTERN = re.compile(
        r"(?m)^\s*Question\s+(?P<number>\d+)\s*[:.-]\s*",
        flags=re.IGNORECASE,
    )

    _OPTION_LINE_PATTERN = re.compile(
        r"^\s*(?:\(?([A-Da-d])\)?[.)])\s+(.+)$"
    )

    _ANSWER_PATTERN = re.compile(
        r"^(?:answer|ans\.?|solution|sol\.?)\s*:?\s*(?P<tail>.*)$",
        flags=re.IGNORECASE,
    )

    _MARKS_PATTERN = re.compile(
        r"[\[(]\s*(\d+)\s*marks?\s*[\])]",
        flags=re.IGNORECASE,
    )

    _NUMBERED_SECTION_PATTERN = re.compile(
        r"^\s*\d+(?:\.\d+)+[.)]?\s+[A-Z][A-Za-z][A-Za-z\s-]{2,}$"
    )

    def extract(
        self,
        chapter,
        document_text: Optional[str] = None,
        next_chapter=None,
    ):
        """
        Populate chapter.exercises.

        The one-argument ExtractionResult return is retained for old direct
        callers that expected stub extractor output.
        """

        if document_text is None:
            return ExtractionResult(
                success=True,
                document_type="exercises",
                metadata={},
                data={
                    "exercises": []
                },
            )

        chapter_text = self._chapter_text(
            chapter,
            document_text,
            next_chapter,
        )

        exercises = []
        seen = set()

        for block in self._exercise_blocks(chapter_text):
            for item in self._question_items(block):
                question = item["question"]

                if not question:
                    continue

                key = self._exercise_key(
                    question,
                    item["options"],
                    item["answer"],
                )

                if key in seen:
                    continue

                seen.add(key)

                order = len(exercises) + 1

                exercise = Exercise(
                    id=self._exercise_id(
                        chapter,
                        order,
                    ),
                    chapter_id=chapter.id,
                    order=order,
                    title=item["title"],
                    source=block["title"],
                    question=question,
                    question_type=item["question_type"],
                    options=item["options"],
                    answer=item["answer"],
                    marks=item["marks"],
                    difficulty=self._difficulty(
                        question,
                        item["options"],
                    ),
                    concept_ids=self._concept_ids(
                        chapter,
                        question,
                    ),
                )

                exercises.append(exercise)

        chapter.exercises = exercises

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

    def _exercise_blocks(
        self,
        chapter_text: str,
    ) -> list[dict]:

        blocks = []
        lines = chapter_text.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            heading = self._BLOCK_HEADING_PATTERN.match(line)

            if heading is None:
                index += 1
                continue

            title = self._block_title(heading)
            body_lines = []
            tail = heading.group("tail").strip()

            if tail:
                body_lines.append(tail)

            index += 1

            while index < len(lines):
                current = lines[index]
                stripped = current.strip()

                if stripped and self._BLOCK_HEADING_PATTERN.match(stripped):
                    break

                if stripped.startswith("#"):
                    break

                if self._NUMBERED_SECTION_PATTERN.match(stripped):
                    break

                body_lines.append(current.rstrip())
                index += 1

            body = "\n".join(body_lines).strip()

            if body:
                blocks.append(
                    {
                        "title": title,
                        "label": heading.group("label"),
                        "body": body,
                    }
                )

        return blocks

    def _question_items(
        self,
        block: dict,
    ) -> list[dict]:

        body = block["body"]
        segments = self._split_numbered_questions(body)

        if not segments and len(self._clean_inline_markdown(body)) >= 8:
            segments = [
                (
                    "",
                    body,
                )
            ]

        items = []

        for number, segment in segments:
            parsed = self._parse_question_segment(
                segment,
                block,
            )

            if not parsed["question"]:
                continue

            title = block["title"]

            if number:
                title = f"{title} Question {number}"

            parsed["title"] = title

            items.append(parsed)

        return items

    def _split_numbered_questions(
        self,
        body: str,
    ) -> list[tuple[str, str]]:

        markers = list(
            self._QUESTION_WORD_MARKER_PATTERN.finditer(body)
        )

        if not markers:
            markers = list(
                self._QUESTION_MARKER_PATTERN.finditer(body)
            )

        if not markers:
            return []

        segments = []

        for index, marker in enumerate(markers):
            start = marker.end()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(body)
            segment = body[start:end].strip()

            if segment:
                segments.append(
                    (
                        marker.group("number"),
                        segment,
                    )
                )

        return segments

    def _parse_question_segment(
        self,
        segment: str,
        block: dict,
    ) -> dict:

        lines = [
            self._clean_line(line)
            for line in segment.splitlines()
        ]

        lines = [
            line
            for line in lines
            if line
        ]

        question_lines = []
        options = []
        answer = ""

        for line in lines:
            option = self._OPTION_LINE_PATTERN.match(line)

            if option:
                options.append(
                    f"{option.group(1).upper()}. {option.group(2).strip()}"
                )
                continue

            answer_match = self._ANSWER_PATTERN.match(line)

            if answer_match:
                tail = answer_match.group("tail").strip()

                if tail:
                    answer = tail

                continue

            question_lines.append(line)

        question = self._join_lines(question_lines)
        inline_options = self._inline_options(question)

        if inline_options:
            question = inline_options["question"]
            options.extend(inline_options["options"])

        marks = self._marks(
            segment,
        )
        question = self._MARKS_PATTERN.sub(
            "",
            question,
        ).strip()
        question = re.sub(
            r"\s+",
            " ",
            question,
        ).strip()

        question_type = self._question_type(
            block,
            question,
            options,
        )

        return {
            "question": question,
            "question_type": question_type,
            "options": options,
            "answer": answer,
            "marks": marks,
            "title": block["title"],
        }

    def _inline_options(
        self,
        question: str,
    ) -> dict | None:

        matches = list(
            re.finditer(
                r"(?:^|\s)([A-Da-d])\)\s+",
                question,
            )
        )

        if len(matches) < 2:
            return None

        stem = question[: matches[0].start()].strip()
        options = []

        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(question)
            options.append(
                f"{match.group(1).upper()}. {question[start:end].strip()}"
            )

        return {
            "question": stem,
            "options": options,
        }

    def _question_type(
        self,
        block: dict,
        question: str,
        options: list[str],
    ) -> str:

        block_text = f"{block.get('title', '')} {block.get('label', '')}".lower()
        question_text = question.lower()

        if "mcq" in block_text or "multiple choice" in block_text or len(options) >= 2:
            return "mcq"

        if "numerical" in block_text:
            return "numerical"

        if (
            re.search(r"\b(find|calculate|evaluate|solve|determine)\b", question_text)
            and re.search(r"\d|=|\\frac|\\sqrt|[+\-*/^]", question)
        ):
            return "numerical"

        if "practice" in block_text:
            return "practice"

        return "question"

    def _marks(
        self,
        text: str,
    ) -> Optional[int]:

        match = self._MARKS_PATTERN.search(text)

        if match is None:
            return None

        return int(match.group(1))

    def _difficulty(
        self,
        question: str,
        options: list[str],
    ) -> str:

        length = len(question) + sum(len(option) for option in options)

        if length > 900:
            return "Hard"

        if length < 220:
            return "Easy"

        return "Medium"

    def _concept_ids(
        self,
        chapter,
        question: str,
    ) -> list[str]:

        text = question.casefold()
        concept_ids = []

        for concept in getattr(chapter, "concepts", []):
            name = getattr(concept, "name", "")

            if not name:
                continue

            if name.casefold() in text:
                concept_ids.append(concept.id)

        return concept_ids

    def _block_title(
        self,
        heading: re.Match[str],
    ) -> str:

        label = " ".join(
            heading.group("label").strip().title().split()
        )
        number = (heading.group("number") or "").strip()

        if label.lower() == "mcqs":
            label = "MCQs"

        if number:
            return f"{label} {number}"

        return label

    def _exercise_id(
        self,
        chapter,
        index: int,
    ) -> str:

        chapter_id = self._document_id(
            getattr(chapter, "id", "") or getattr(chapter, "name", "")
        )

        return f"{chapter_id}_exercise_{index:03d}"

    def _exercise_key(
        self,
        question: str,
        options: list[str],
        answer: str,
    ) -> str:

        return re.sub(
            r"\s+",
            "",
            f"{question}\n{options}\n{answer}".casefold(),
        )

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

        return document_id or "exercise"

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
