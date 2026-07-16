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
from dataclasses import dataclass
from enum import Enum

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Section,
)
from .models import HeadingCandidate
class BlockType(str, Enum):

    CHAPTER = "chapter"

    SECTION = "section"

    SUBSECTION = "subsection"

    DEFINITION = "definition"

    PROPERTY = "property"

    THEOREM = "theorem"

    NOTE = "note"

    EXAMPLE = "example"

    EXERCISE = "exercise"

    FIGURE = "figure"

    TABLE = "table"

    FORMULA = "formula"

    TEXT = "text"

    UNKNOWN = "unknown"


@dataclass(slots=True)
class DocumentBlock:

    text: str

    level: int

    number: str

    title: str

    block_type: BlockType

    start: int

    end: int


class SectionParser:
    
    _SKIP_HEADINGS = {

    "exercise",

    "exercises",

    "example",

    "examples",

    "worked example",

    "illustration",

    "activity",

    "objective",

    "objectives",

    "summary",

    "solutions",

    "solution",

    "remarks",

    "remark",

    "proof",

    "answer",

    "answers",

    "questions",

    "question",

    "figure",

    "table",

}

    _FORMULA_PATTERN = re.compile(

        r"(=|\\frac|\\sqrt|\\sum|\\int|\\lim|\\sin|\\cos|\\tan)"

    )

    _OCR_NOISE = re.compile(

        r"^[A-Za-z0-9\-]{1,8}$"

    )

    _MAX_TITLE_WORDS = 12

    _MIN_TITLE_WORDS = 1

    """
    Converts chapter markdown into structured sections.
    """

    _heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+)$"
    )

    _number_pattern = re.compile(
        r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.+)$"
    )
    
    _HEADER_PATTERNS = (

        re.compile(r"^page\s+\d+$", re.IGNORECASE),

        re.compile(r"^\d+\s*$"),

        re.compile(r"^chapter\s+\d+", re.IGNORECASE),

        re.compile(r"^jee", re.IGNORECASE),

        re.compile(r"^ncert", re.IGNORECASE),

    )

    _FOOTER_PATTERNS = (

        re.compile(r"^copyright", re.IGNORECASE),

        re.compile(r"^www\.", re.IGNORECASE),

        re.compile(r"^https?://", re.IGNORECASE),

    )

    _REPEAT_THRESHOLD = 2

    def parse(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        markdown = self._remove_headers_and_footers(
            chapter.raw_markdown
        )

        markers = self._find_document_blocks(markdown)

        if not markers:
            return chapter

        sections: list[Section] = []
        seen_section_ids: dict[str, int] = {}

        for index, marker in enumerate(markers):

            content_start = marker["end"]

            content_end = self._section_content_end(
                index,
                markers,
                len(markdown),
            )

            content = self._clean_section_content(

                markdown[
                    content_start:content_end
                ]

            )

            section_id = self._unique_section_id(
                self._section_id(
                    str(marker["number"]),
                    str(marker["title"]),
                ),
                seen_section_ids,
            )

            section = Section(
                section_id=section_id,
                number=str(marker["number"]),
                title=str(marker["title"]),
                level=int(marker["level"]),
                content=content,
            )

            sections.append(section)
            
        sections = self._merge_continuation_sections(

            sections

        )

        self._link_hierarchy(sections)

        chapter.sections = sections
        print("=" * 80)
        print(
            f"SectionParser: "
            f"{len(chapter.sections)} sections"
        )
        for section in chapter.sections:
            print(
                f"{section.number} "
                f"{section.title}"
            )
        print("=" * 80)

        return chapter
    
    
    
    def _heading_score(
        self,
        number: str,
        title: str,
    ) -> float:

        score = 0.0

        title = title.strip()

        #
        # numbered headings
        #

        if number:
            score += 0.40

        #
        # title length
        #

        words = len(title.split())

        if 1 <= words <= 6:
            score += 0.20

        elif words <= 10:
            score += 0.10

        #
        # title case
        #

        first = next(
            (c for c in title if c.isalpha()),
            "",
        )

        if first.isupper():
            score += 0.15

        #
        # common textbook headings
        #

        heading_words = (
            "definition",
            "example",
            "exercise",
            "proof",
            "remark",
            "activity",
            "algorithm",
            "note",
            "summary",
            "theorem",
            "lemma",
            "corollary",
        )

        lower = title.lower()

        if any(
            lower.startswith(word)
            for word in heading_words
        ):
            score += 0.20

        #
        # punctuation penalty
        #

        if title.endswith("."):
            score -= 0.10

        #
        # equations
        #

        if re.search(
            r"[=<>±÷×]",
            title,
        ):
            score -= 0.30

        #
        # OCR fragments
        #

        if len(re.findall(r"[A-Za-z]", title)) < 3:
            score -= 0.40

        return score
    
    def _candidate_heading(
        self,
        marker: dict,
    ) -> HeadingCandidate:

        return HeadingCandidate(
            start=marker["start"],
            end=marker["end"],
            number=str(marker["number"]),
            title=str(marker["title"]),
            level=int(marker["level"]),
            score=self._heading_score(
                str(marker["number"]),
                str(marker["title"]),
            ),
        )
    
    def _deduplicate_candidates(
        self,
        blocks: list[dict],
    ) -> list[dict]:

        unique: dict[
            tuple[str, str],
            dict,
        ] = {}

        for block in blocks:

            key = (
                block["number"],
                block["title"].lower().strip(),
            )

            previous = unique.get(key)

            if previous is None:

                unique[key] = block

                continue

            #
            # Keep the earliest occurrence.
            #
            if block["start"] < previous["start"]:

                unique[key] = block

        return sorted(
            unique.values(),
            key=lambda x: x["start"],
        )
        
    def _valid_numbering(
        self,
        number: str,
    ) -> bool:

        if not number:
            return True

        #
        # Allow:
        #
        # 3
        # 3.1
        # 3.1.2
        #
        if re.fullmatch(
            r"\d+(?:\.\d+)*",
            number,
        ):
            return True

        #
        # Roman numerals.
        #
        if re.fullmatch(
            r"[IVXLCDM]+",
            number,
            re.I,
        ):
            return True

        return False
    
    def _looks_like_ocr_noise(
        self,
        title: str,
    ) -> bool:

        title = title.strip()

        #
        # Very short.
        #
        if len(title) <= 2:
            return True

        #
        # Too many symbols.
        #
        letters = len(
            re.findall(
                r"[A-Za-z]",
                title,
            )
        )

        digits = len(
            re.findall(
                r"\d",
                title,
            )
        )

        symbols = len(
            re.findall(
                r"[^A-Za-z0-9\s]",
                title,
            )
        )

        if letters == 0:
            return True

        if symbols > letters:
            return True

        #
        # OCR garbage like:
        #
        # xn
        # ab
        # 0 shed
        #
        if (
            letters <= 3
            and digits > 0
        ):
            return True

        return False
    
    
    def _section_content_end(
        self,
        index: int,
        markers: list[dict[str, int | str]],
        markdown_length: int,
    ) -> int:

        current = markers[index]

        current_level = int(
            current["level"]
        )

        for next_marker in markers[index + 1:]:

            next_level = int(
                next_marker["level"]
            )

            #
            # Same or higher hierarchy
            # starts a new section.
            #

            if next_level <= current_level:

                return int(
                    next_marker["start"]
                )

        return markdown_length
    
    def _clean_section_content(
        self,
        content: str,
    ) -> str:

        #
        # Remove Azure comments
        #

        content = re.sub(

            r"<!--.*?-->",

            "",

            content,

            flags=re.DOTALL,

        )

        #
        # Remove merge separators
        #

        content = re.sub(

            r"\n={10,}\n",

            "\n",

            content,

        )

        #
        # Remove repeated blank lines
        #

        content = re.sub(

            r"\n{3,}",

            "\n\n",

            content,

        )

        #
        # Remove trailing spaces
        #

        lines = [

            line.rstrip()

            for line in content.splitlines()

        ]

        return "\n".join(lines).strip()

    def _find_document_blocks(

        self,

        markdown: str,

    ) -> list[dict]:

        blocks: list[dict] = []

        offset = 0

        for line in markdown.splitlines(
            keepends=True,
        ):

            parsed = self._parse_marker(
                line.rstrip(),
            )

            if parsed is None:

                offset += len(line)

                continue

            #
            # Score this heading.
            #
            candidate = self._candidate_heading(
                parsed,
            )
            
            if not self._valid_numbering(
                candidate.number,
            ):

                offset += len(line)

                continue
            
            if self._looks_like_ocr_noise(
                candidate.title,
            ):

                offset += len(line)

                continue

            #
            # Reject weak headings.
            #
            if candidate.score < 0.50:

                offset += len(line)

                continue

            #
            # Existing validation.
            #
            if not self._accept_heading(
                candidate.number,
                candidate.title,
                candidate.level,
            ):

                offset += len(line)

                continue

            blocks.append(
                {
                    "start": offset,
                    "end": offset + len(line),
                    "level": candidate.level,
                    "number": candidate.number,
                    "title": candidate.title,
                    "block_type": parsed["block_type"],
                }
            )

            offset += len(line)

        blocks = self._deduplicate_candidates(
            blocks,
        )

        return blocks
    
    
    
    def _looks_like_heading(
        self,
        number: str,
        title: str,
    ) -> bool:
        """
        Fast heuristic used by _parse_marker().

        Rejects obvious paragraph text before running the
        more expensive heading validation.
        """

        title = (title or "").strip()

        if not title:
            return False

        #
        # Long sentences are paragraphs.
        #
        words = title.split()

        if len(words) > 8:
            return False

        if len(title) > 80:
            return False

        #
        # First alphabetic character should normally
        # be uppercase.
        #
        first = next(
            (c for c in title if c.isalpha()),
            "",
        )

        if first and first.islower():
            return False

        #
        # Ignore equations.
        #
        if re.search(
            r"[=+\-×÷<>]",
            title,
        ):
            return False

        #
        # OCR fragments.
        #
        letters = re.findall(
            r"[A-Za-z]",
            title,
        )

        if len(letters) < 4:
            return False

        return True


    def _parse_marker(
        self,
        line: str,
    ) -> dict | None:

        original = line

        line = re.sub(
            r"\s+",
            " ",
            line.strip(),
        )

        if not line:
            return None

        #
        # Remove markdown heading markers.
        #
        line = re.sub(
            r"^#+\s*",
            "",
            line,
        )

        #
        # Ignore bullets.
        #
        if re.match(
            r"^[-*•]",
            line,
        ):
            return None

        #
        # Ignore obvious paragraphs.
        #
        if len(line.split()) > 14:
            return None

        #
        # --------------------------------------------------------
        # Numbered headings
        #
        # 3 Matrix
        # 3.2 Matrix
        # 3.2.1 Order of Matrix
        # --------------------------------------------------------
        #

        number, title = self._split_number(line)

        if number:

            level = number.count(".") + 1

            return {
                "number": number,
                "title": title.strip(),
                "level": level,
                "block_type": "section",
            }

        #
        # --------------------------------------------------------
        # Exercise 3.1
        # Example 5
        # --------------------------------------------------------
        #

        m = re.match(
            r"^(Exercise|Example)\s+(\d+(?:\.\d+)*)$",
            line,
            re.I,
        )

        if m:

            return {
                "number": m.group(2),
                "title": m.group(1).title(),
                "level": 2,
                "block_type": m.group(1).lower(),
            }

        #
        # --------------------------------------------------------
        # Generic textbook headings
        # --------------------------------------------------------
        #

        generic = {

            "definition",
            "definitions",
            "theorem",
            "theorems",
            "proof",
            "proofs",
            "algorithm",
            "algorithms",
            "note",
            "notes",
            "remark",
            "remarks",
            "property",
            "properties",
            "observation",
            "observations",
            "example",
            "examples",
            "exercise",
            "exercises",
            "summary",
            "review",
            "activity",
            "activities",
            "objective",
            "objectives",
            "formula",
            "formulae",
            "result",
            "results",
            "application",
            "applications",
        }

        lower = line.lower()

        if lower in generic:

            return {
                "number": "",
                "title": line,
                "level": 1,
                "block_type": "heading",
            }

        #
        # --------------------------------------------------------
        # Short title-case headings
        #
        # Matrix
        # Types of Matrix
        # Linear Equation
        # --------------------------------------------------------
        #

        if self._looks_like_heading(line):

            return {
                "number": "",
                "title": line,
                "level": 1,
                "block_type": "heading",
            }

        return None
            
    def _classify_heading(
        self,
        title: str,
    ) -> BlockType | None:

        lower = title.lower().strip()

        

        if lower.startswith(
            "definition"
        ):
            return BlockType.DEFINITION

        if lower.startswith(
            "property"
        ):
            return BlockType.PROPERTY

        if lower.startswith(
            "theorem"
        ):
            return BlockType.THEOREM

        if lower.startswith(
            "note"
        ):
            return BlockType.NOTE

        if lower.startswith(
            "figure"
        ):
            return BlockType.FIGURE

        if lower.startswith(
            "table"
        ):
            return BlockType.TABLE

        if lower.startswith(
            "exercise"
        ):
            return BlockType.EXERCISE

        if lower.startswith(
            "example"
        ):
            return BlockType.EXAMPLE

        return BlockType.SECTION

    def _split_number(
        self,
        line: str,
    ) -> tuple[str, str]:

        line = re.sub(
            r"\s+",
            " ",
            line.strip(),
        )

        #
        # 3 Matrix
        # 3.2 Matrix
        # 3.2.1 Order of Matrix
        #
        m = re.match(
            r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.+)$",
            line,
        )

        if m:

            number = m.group(1).strip()
            title = m.group(2).strip()

            #
            # Reject OCR like:
            #
            # 1 xn
            # 2 ab
            # 5 ivcos2
            #

            letters = re.findall(
                r"[A-Za-z]",
                title,
            )

            if len(letters) < 3:
                return "", line

            words = title.split()

            #
            # Reject if every word is tiny.
            #

            if all(len(w) <= 2 for w in words):
                return "", line

            return number, title

        #
        # Exercise 3.1
        # Example 4
        #

        m = re.match(
            r"^(Exercise|Example)\s+(\d+(?:\.\d+)*)\s*$",
            line,
            re.I,
        )

        if m:

            return (
                m.group(2),
                m.group(1).title(),
            )

        #
        # Plain headings.
        #

        return "", line

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

    def _unique_section_id(
        self,
        section_id: str,
        seen_section_ids: dict[str, int],
    ) -> str:

        count = seen_section_ids.get(section_id, 0) + 1
        seen_section_ids[section_id] = count

        if count == 1:
            return section_id

        return f"{section_id}-{count}"

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
    
    def _remove_headers_and_footers(

        self,

        markdown: str,

    ) -> str:

        cleaned = []

        for line in markdown.splitlines():

            text = line.strip()

            if not text:

                cleaned.append("")

                continue

            discard = False

            for pattern in self._HEADER_PATTERNS:

                if pattern.match(text):

                    discard = True

                    break

            if discard:

                continue

            for pattern in self._FOOTER_PATTERNS:

                if pattern.match(text):

                    discard = True

                    break

            if discard:

                continue

            cleaned.append(line)

        return "\n".join(cleaned)
