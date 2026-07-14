from __future__ import annotations

import re
from typing import Optional

from models import (
    ExtractionResult,
    Formula,
)


class FormulaExtractor:

    """
    Extracts mathematical formulas.
    """

    _DELIMITED_MATH_PATTERNS = (
        re.compile(r"\$\$(.+?)\$\$", flags=re.DOTALL),
        re.compile(r"\\\[(.+?)\\\]", flags=re.DOTALL),
        re.compile(r"\\\((.+?)\\\)", flags=re.DOTALL),
        re.compile(r"(?<!\$)\$([^$\n]{2,})\$(?!\$)"),
    )

    _RELATION_PATTERN = re.compile(
        r"(=|<=|>=|<|>|!=|\\leq?|\\geq?|\\approx|\\equiv|\\ne|"
        "\u2264|\u2265|\u2260)"
    )

    _MATH_SYMBOL_PATTERN = re.compile(
        r"[A-Za-z]\s*(?:[_^]|\d|=)|"
        r"(?:\\frac|\\sqrt|\\sin|\\cos|\\tan|\\log|\\ln|sqrt\s*\()|"
        r"[+\-*/^=(){}\[\]]|"
        "[\u221a\u03c0\u03b8\u03b1\u03b2\u03b3\u0394\u2211\u222b\u00b1]"
    )

    _SKIPPED_SECTION_PATTERN = re.compile(
        r"^(exercise|exercises|miscellaneous exercise)\b",
        flags=re.IGNORECASE,
    )

    _LATEX_COMMANDS = {
        "alpha",
        "approx",
        "beta",
        "cos",
        "cot",
        "cosec",
        "delta",
        "div",
        "equiv",
        "frac",
        "gamma",
        "ge",
        "geq",
        "in",
        "int",
        "le",
        "leq",
        "ln",
        "log",
        "ne",
        "pi",
        "pm",
        "sec",
        "sin",
        "sqrt",
        "sum",
        "tan",
        "theta",
        "times",
    }

    _WORD_VARIABLE_EXCLUSIONS = {
        "and",
        "are",
        "for",
        "if",
        "is",
        "or",
        "the",
        "then",
        "where",
        "with",
    }

    def extract(
        self,
        chapter,
        document_text: Optional[str] = None,
        next_chapter=None,
    ):
        """
        Populate chapter.formulas deterministically.

        The one-argument ExtractionResult return is retained for older callers
        that imported the stub directly.
        """

        if document_text is None:
            return ExtractionResult(
                success=True,
                document_type="formulas",
                metadata={},
                data={
                    "formulas": []
                }
            )

        chapter_text = self._chapter_text(
            chapter,
            document_text,
            next_chapter,
        )

        chapter_text = self._remove_skipped_blocks(
            chapter_text,
        )

        formulas = []
        seen = set()

        for expression, context in self._formula_candidates(chapter_text):
            latex = self._normalize_latex(expression)

            if not self._is_formula_candidate(latex):
                continue

            key = self._formula_key(latex)

            if key in seen:
                continue

            seen.add(key)

            order = len(formulas) + 1

            formula = Formula(
                id=self._formula_id(
                    chapter,
                    order,
                ),
                chapter_id=chapter.id,
                order=order,
                latex=latex,
                variables=self._variables(latex),
                description=self._description(
                    chapter.name,
                    context,
                ),
                meaning=self._meaning(
                    chapter.name,
                    context,
                ),
                concept_ids=self._concept_ids(
                    chapter,
                    context,
                    latex,
                ),
            )

            formulas.append(formula)

        chapter.formulas = formulas

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

    def _formula_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:

        candidates = []

        candidates.extend(
            self._delimited_math_candidates(content)
        )

        candidates.extend(
            self._equation_line_candidates(content)
        )

        return candidates

    def _delimited_math_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:

        candidates = []

        for pattern in self._DELIMITED_MATH_PATTERNS:
            for match in pattern.finditer(content):
                candidates.append(
                    (
                        match.group(1),
                        self._nearest_context(
                            content,
                            match.start(),
                            match.end(),
                        ),
                    )
                )

        return candidates

    def _equation_line_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:

        candidates = []
        previous_text_line = ""

        for line in content.splitlines():
            stripped = self._clean_line(line)

            if not stripped:
                continue

            if self._is_context_line(stripped):
                previous_text_line = ""
                continue

            if "$" in stripped:
                continue

            if not self._looks_like_equation_line(stripped):
                previous_text_line = stripped
                continue

            candidates.append(
                (
                    stripped,
                    previous_text_line,
                )
            )

        return candidates

    def _looks_like_equation_line(
        self,
        line: str,
    ) -> bool:

        if len(line) > 180:
            return False

        if line.startswith(("#", "|", "<")):
            return False

        if not self._RELATION_PATTERN.search(line):
            return False

        if not self._MATH_SYMBOL_PATTERN.search(line):
            return False

        words = re.findall(
            r"[A-Za-z]{3,}",
            re.sub(r"\\[A-Za-z]+", "", line),
        )

        return len(words) <= 8

    def _is_formula_candidate(
        self,
        latex: str,
    ) -> bool:

        return (
            3 <= len(latex) <= 220
            and bool(self._RELATION_PATTERN.search(latex))
            and bool(self._MATH_SYMBOL_PATTERN.search(latex))
        )

    def _nearest_context(
        self,
        content: str,
        start: int,
        end: int,
    ) -> str:

        before = content[:start].splitlines()
        after = content[end:].splitlines()

        for line in reversed(before):
            cleaned = self._clean_line(line)

            if cleaned and not self._is_context_line(cleaned):
                return cleaned

        for line in after:
            cleaned = self._clean_line(line)

            if cleaned and not self._is_context_line(cleaned):
                return cleaned

        return ""

    def _meaning(
        self,
        chapter_name: str,
        context: str,
    ) -> str:

        cleaned = self._clean_inline_markdown(context)

        if cleaned:
            return cleaned

        return f"Formula from {chapter_name}".strip()

    def _description(
        self,
        chapter_name: str,
        context: str,
    ) -> str:

        meaning = self._meaning(
            chapter_name,
            context,
        )

        return meaning.rstrip(":")

    def _variables(
        self,
        latex: str,
    ) -> list[str]:

        without_commands = re.sub(
            r"\\[A-Za-z]+",
            " ",
            latex,
        )

        candidates = re.findall(
            r"\b[A-Za-z](?:_\{?[A-Za-z0-9]+\}?|_\d+)?\b",
            without_commands,
        )

        variables = []
        seen = set()

        for variable in candidates:
            normalized = variable.replace("{", "").replace("}", "")
            key = normalized.lower()

            if key in self._LATEX_COMMANDS:
                continue

            if key in self._WORD_VARIABLE_EXCLUSIONS:
                continue

            if key in seen:
                continue

            seen.add(key)
            variables.append(normalized)

        return variables

    def _concept_ids(
        self,
        chapter,
        context: str,
        latex: str,
    ) -> list[str]:

        text = f"{context} {latex}".casefold()
        concept_ids = []

        for concept in getattr(chapter, "concepts", []):
            name = getattr(concept, "name", "")

            if not name:
                continue

            if name.casefold() in text:
                concept_ids.append(concept.id)

        return concept_ids

    def _formula_id(
        self,
        chapter,
        index: int,
    ) -> str:

        chapter_id = self._document_id(
            getattr(chapter, "id", "") or getattr(chapter, "name", "")
        )

        return f"{chapter_id}_formula_{index:03d}"

    def _formula_key(
        self,
        latex: str,
    ) -> str:

        return re.sub(
            r"\s+",
            "",
            latex.casefold(),
        )

    def _normalize_latex(
        self,
        expression: str,
    ) -> str:

        latex = self._clean_inline_markdown(
            expression,
            preserve_underscores=True,
        )

        replacements = {
            "\u2264": r"\le",
            "\u2265": r"\ge",
            "\u2260": r"\ne",
            "\u00d7": r"\times",
            "\u00f7": r"\div",
            "\u2212": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u00b1": r"\pm",
            "\u221a": r"\sqrt",
            "\u03c0": r"\pi",
            "\u03b8": r"\theta",
            "\u03b1": r"\alpha",
            "\u03b2": r"\beta",
            "\u03b3": r"\gamma",
            "\u0394": r"\Delta",
            "\u00b2": "^2",
            "\u00b3": "^3",
        }

        for source, replacement in replacements.items():
            latex = latex.replace(
                source,
                replacement,
            )

        latex = re.sub(
            r"\bsqrt\s*\(",
            r"\\sqrt(",
            latex,
            flags=re.IGNORECASE,
        )

        latex = re.sub(
            r"(\\(?:alpha|beta|gamma|Delta|pi|theta))(?=[A-Za-z])",
            r"\1 ",
            latex,
        )

        latex = re.sub(
            r"\s+",
            " ",
            latex,
        )

        return latex.strip()

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

        return self._clean_inline_markdown(
            cleaned.strip(),
            preserve_underscores=True,
        )

    def _is_context_line(
        self,
        line: str,
    ) -> bool:

        return (
            line.startswith(("#", "<!--", "|", "```"))
            or bool(re.fullmatch(r"[-=_\s]+", line))
        )

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

        return document_id or "formula"

    @staticmethod
    def _clean_inline_markdown(
        text: str,
        preserve_underscores: bool = False,
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

        if not preserve_underscores:
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

        if not preserve_underscores:
            cleaned = re.sub(
                r"(?<!_)_([^_]+)_(?!_)",
                r"\1",
                cleaned,
            )

        return cleaned.strip()
