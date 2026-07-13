"""
MathVerse Knowledge Factory

Formula Extractor

Deterministically extracts mathematical formulas from parsed sections.

No AI.
No Firestore.
Consumes SectionParser and ConceptExtractor output.
"""

from __future__ import annotations

import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Formula,
)
from app.services.knowledge_factory.section_content import (
    local_section_content,
)


class FormulaExtractor:
    """
    Builds Formula objects from parsed chapter sections.
    """

    _DELIMITED_MATH_PATTERNS = (
        re.compile(r"\$\$(.+?)\$\$", flags=re.DOTALL),
        re.compile(r"\\\[(.+?)\\\]", flags=re.DOTALL),
        re.compile(r"\\\((.+?)\\\)", flags=re.DOTALL),
        re.compile(r"(?<!\$)\$([^$\n]{2,})\$(?!\$)"),
    )

    _EQUATION_OPERATOR_PATTERN = re.compile(
        r"(=|≤|≥|<|>|\\leq?|\\geq?|\\approx|\\equiv|≠|\\ne)"
    )

    _MATH_SYMBOL_PATTERN = re.compile(
        r"[A-Za-z]\s*(?:[_^]|\d|=)|"
        r"(?:\\frac|\\sqrt|\\sin|\\cos|\\tan|\\log|\\ln|\\pi)|"
        r"[+\-*/^=(){}\[\]√πθαβγΔ∑∫≤≥±]"
    )

    _SKIPPED_SECTION_PATTERN = re.compile(
        r"^(exercise|exercises|miscellaneous exercise)\b",
        flags=re.IGNORECASE,
    )

    _UNIT_PATTERN = re.compile(
        r"\b(?:mm|cm|m|km|g|kg|s|sec|second|seconds|min|minute|minutes|"
        r"h|hr|hour|hours|unit|units|degree|degrees)\b|°",
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
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        formulas: list[Formula] = []
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
            section.formula_ids = []

        for concept in chapter.concepts:
            concept.formula_ids = []

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
            candidates = self._formula_candidates(content)

            for expression, context in candidates:
                latex = self._normalize_latex(expression)

                if not self._is_formula_candidate(latex):
                    continue

                key = self._formula_key(latex)

                if key in seen:
                    continue

                seen.add(key)

                formula_id = self._formula_id(
                    section.section_id,
                    len(section.formula_ids) + 1,
                )

                formula = Formula(
                    formula_id=formula_id,
                    title=self._title(section.title, latex),
                    latex=latex,
                    meaning=self._meaning(section.title, context),
                    variables=self._variables(latex),
                    units=self._units(f"{context}\n{latex}"),
                    description=self._description(section.title, context),
                    section_id=section.section_id,
                    concept_ids=list(concept_ids),
                )

                formulas.append(formula)
                section.formula_ids.append(formula.formula_id)

                for concept_id in concept_ids:
                    concept = concepts_by_id.get(concept_id)

                    if concept is None:
                        continue

                    if formula.formula_id not in concept.formula_ids:
                        concept.formula_ids.append(formula.formula_id)

        chapter.formulas = formulas

        return chapter

    def _formula_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:

        candidates: list[tuple[str, str]] = []

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

        candidates: list[tuple[str, str]] = []

        for pattern in self._DELIMITED_MATH_PATTERNS:
            for match in pattern.finditer(content):
                expression = match.group(1)
                context = self._nearest_context(
                    content,
                    match.start(),
                    match.end(),
                )
                candidates.append(
                    (
                        expression,
                        context,
                    )
                )

        return candidates

    def _equation_line_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:

        candidates: list[tuple[str, str]] = []
        previous_text_line = ""

        for line in content.splitlines():
            stripped = self._clean_line(line)

            if not stripped:
                continue

            if self._is_context_line(stripped):
                previous_text_line = stripped
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

        if not self._EQUATION_OPERATOR_PATTERN.search(line):
            return False

        if not self._MATH_SYMBOL_PATTERN.search(line):
            return False

        words = re.findall(
            r"[A-Za-z]{3,}",
            re.sub(r"\\[A-Za-z]+", "", line),
        )

        return len(words) <= 8

    def _is_context_line(
        self,
        line: str,
    ) -> bool:

        return (
            line.startswith(("#", "<!--", "|", "```"))
            or bool(re.fullmatch(r"[-=_\s]+", line))
        )

    def _is_formula_candidate(
        self,
        latex: str,
    ) -> bool:

        if len(latex) < 3:
            return False

        if len(latex) > 220:
            return False

        if not self._EQUATION_OPERATOR_PATTERN.search(latex):
            return False

        return bool(self._MATH_SYMBOL_PATTERN.search(latex))

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

    def _title(
        self,
        section_title: str,
        latex: str,
    ) -> str:

        if section_title:
            return section_title

        return latex[:80]

    def _meaning(
        self,
        section_title: str,
        context: str,
    ) -> str:

        cleaned = self._clean_inline_markdown(context)

        if cleaned:
            return cleaned

        return f"Formula from {section_title}".strip()

    def _description(
        self,
        section_title: str,
        context: str,
    ) -> str:

        meaning = self._meaning(
            section_title,
            context,
        )

        if meaning:
            return meaning

        return section_title.strip()

    def _variables(
        self,
        latex: str,
    ) -> list[str]:

        without_commands = re.sub(
            r"\\[A-Za-z]+",
            " ",
            latex,
        )

        candidates: list[str] = []

        candidates.extend(
            re.findall(
                r"\b[A-Za-z](?:_\{?[A-Za-z0-9]+\}?|_\d+)?\b",
                without_commands,
            )
        )

        candidates.extend(
            re.findall(
                r"\b[A-Za-z]\b",
                without_commands,
            )
        )

        variables: list[str] = []
        seen: set[str] = set()

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

    def _units(
        self,
        text: str,
    ) -> list[str]:

        units: list[str] = []
        seen: set[str] = set()

        for match in self._UNIT_PATTERN.finditer(text):
            unit = match.group(0).lower()

            if unit == "°":
                unit = "degrees"

            key = unit.rstrip("s")

            if key in seen:
                continue

            seen.add(key)
            units.append(unit)

        return units

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

    def _formula_id(
        self,
        section_id: str,
        index: int,
    ) -> str:

        return f"{section_id}-formula-{index:03d}"

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
            "≤": r"\le",
            "≥": r"\ge",
            "≠": r"\ne",
            "×": r"\times",
            "÷": r"\div",
            "−": "-",
            "–": "-",
            "—": "-",
            "±": r"\pm",
            "√": r"\sqrt",
            "π": r"\pi",
            "θ": r"\theta",
            "α": r"\alpha",
            "β": r"\beta",
            "γ": r"\gamma",
            "Δ": r"\Delta",
            "²": "^2",
            "³": "^3",
        }

        for source, replacement in replacements.items():
            latex = latex.replace(
                source,
                replacement,
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

        cleaned = cleaned.strip()

        return self._clean_inline_markdown(
            cleaned,
            preserve_underscores=True,
        )

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
