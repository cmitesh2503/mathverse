"""
MathVerse Knowledge Factory

Concept Extractor

Builds teachable mathematical concepts from
parsed chapter sections.

Version 2
---------
Deterministic.

No LLM.

No Gemini.

Consumes SectionParser output.
"""

from __future__ import annotations

from collections import Counter
import re

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    Concept,
)


class ConceptExtractor:
    """
    Builds Concept objects from parsed sections.
    """

    _EXCLUDED_TITLES = {
        "introduction",
        "summary",
        "miscellaneous exercise",
    }

    _QUOTE_PATTERNS = (
        "essence of mathematics",
    )

    _EXERCISE_PATTERN = re.compile(
        r"^(exercise|exercises|miscellaneous exercise)\b",
        flags=re.IGNORECASE,
    )

    _EXAMPLE_PATTERN = re.compile(
        r"^(?:#{1,6}\s+)?"
        r"(?:solved\s+example|worked\s+example|example|illustration)\b",
        flags=re.IGNORECASE,
    )

    _ALIAS_PATTERN = re.compile(
        r"\b(?:also\s+called|called|known\s+as|abbreviated\s+as)\s+"
        r"([A-Za-z][A-Za-z0-9\s\-]{2,80})",
        flags=re.IGNORECASE,
    )

    _PREREQUISITE_PATTERN = re.compile(
        r"\b(?:using|recall|as\s+learned\s+in|previously\s+studied|based\s+on)\s+"
        r"([A-Za-z][A-Za-z0-9\s\-]{2,80})",
        flags=re.IGNORECASE,
    )

    _STOPWORDS = {
        "a",
        "about",
        "above",
        "after",
        "again",
        "also",
        "an",
        "another",
        "because",
        "been",
        "before",
        "being",
        "between",
        "called",
        "chapter",
        "does",
        "each",
        "every",
        "example",
        "from",
        "given",
        "have",
        "into",
        "learned",
        "matrix",
        "more",
        "only",
        "other",
        "same",
        "section",
        "should",
        "such",
        "than",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "through",
        "under",
        "using",
        "where",
        "which",
        "with",
    }

    def extract(
        self,
        chapter: ChapterKnowledge,
    ) -> ChapterKnowledge:

        concepts: list[Concept] = []

        seen: set[str] = set()

        for section in chapter.sections:
            section.concept_ids = []

        for section in chapter.sections:

            title = section.title.strip()

            if not title:
                continue

            title_lower = title.lower()

            # Skip chapter title
            if title_lower == chapter.metadata.title.lower():
                continue

            if title_lower in self._EXCLUDED_TITLES:
                continue

            # Skip famous quotes
            if any(pattern in title_lower for pattern in self._QUOTE_PATTERNS):
                continue

            # Skip exercises
            if self._EXERCISE_PATTERN.match(title):
                continue

            slug = self._slug(title)

            if slug in seen:
                continue

            seen.add(slug)

            description = self._first_meaningful_paragraph(
                section.content
            )
            aliases = self._aliases(
                title,
                section.content,
            )
            keywords = self._keywords(
                title,
                section.content,
            )
            examples = self._examples(
                section.content,
            )

            concept = Concept(
                concept_id=slug,
                title=title,
                section_id=section.section_id,
                section_number=section.number,
                chapter_id=chapter.metadata.chapter_id,
                curriculum_id=chapter.metadata.curriculum_id,
                description=description,
                aliases=aliases,
                keywords=keywords,
                examples=examples,
                prerequisites=self._prerequisites(
                    section.content,
                ),
                learning_objectives=self._learning_objectives(
                    title,
                    description,
                    section.content,
                ),
                difficulty=self._difficulty(
                    title,
                    section.content,
                    int(section.level),
                ),
            )

            concepts.append(concept)

            section.concept_ids.append(concept.concept_id)

        self._populate_related_concepts(
            concepts,
            chapter.sections,
        )

        chapter.concepts = concepts

        return chapter

    def _first_meaningful_paragraph(self, text: str) -> str:
        """
        Returns the first non-empty non-heading non-example paragraph.
        """

        if not text:
            return ""

        for paragraph in self._paragraph_blocks(text):
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            if self._is_heading(paragraph):
                continue

            if self._is_example(paragraph):
                continue

            if self._is_noise(paragraph):
                continue

            return self._clean_inline_markdown(paragraph)

        return ""

    def _keywords(
        self,
        title: str,
        content: str,
    ) -> list[str]:

        candidates: list[str] = []

        candidates.extend(
            self._formatted_terms(content)
        )

        candidates.extend(
            self._math_identifiers(content)
        )

        candidates.extend(
            self._repeated_terms(
                f"{title}\n\n{content}"
            )
        )

        return self._unique(
            self._normalize_term(term)
            for term in candidates
            if self._normalize_term(term)
        )

    def _aliases(
        self,
        title: str,
        content: str,
    ) -> list[str]:

        aliases: list[str] = []

        aliases.extend(
            re.findall(
                r"\(([^()]{3,80})\)",
                f"{title}\n{content}",
            )
        )

        for match in self._ALIAS_PATTERN.finditer(content):
            aliases.extend(
                self._split_alias_phrase(match.group(1))
            )

        aliases.extend(
            re.findall(
                r"\bor\s+([A-Z][A-Za-z0-9\s\-]{2,60})",
                content,
            )
        )

        return self._unique(
            self._normalize_term(term)
            for term in aliases
            if self._normalize_term(term)
        )

    def _split_alias_phrase(
        self,
        phrase: str,
    ) -> list[str]:

        return [
            part.strip()
            for part in re.split(
                r"\s+(?:or|and)\s+|[,;/]",
                phrase,
            )
            if part.strip()
        ]

    def _prerequisites(
        self,
        content: str,
    ) -> list[str]:

        return self._unique(
            self._normalize_term(match.group(1))
            for match in self._PREREQUISITE_PATTERN.finditer(content)
            if self._normalize_term(match.group(1))
        )

    def _examples(
        self,
        content: str,
    ) -> list[str]:

        examples: list[str] = []

        lines = content.splitlines()

        index = 0

        while index < len(lines):
            line = lines[index]

            if not self._EXAMPLE_PATTERN.match(line.strip()):
                index += 1
                continue

            block = [line.rstrip()]

            index += 1

            while index < len(lines):
                next_line = lines[index]
                stripped = next_line.strip()

                if stripped.startswith("#"):
                    break

                if (
                    stripped
                    and self._EXAMPLE_PATTERN.match(stripped)
                    and any(item.strip() for item in block)
                ):
                    break

                block.append(next_line.rstrip())

                index += 1

            examples.append(
                "\n".join(block).strip()
            )

        return self._unique(examples)

    def _learning_objectives(
        self,
        title: str,
        description: str,
        content: str,
    ) -> list[str]:

        objectives = [
            f"Explain {title} in your own words.",
        ]

        if description:
            objectives.append(
                f"Identify where {title} is used in the chapter."
            )

        if self._examples(content):
            objectives.append(
                f"Solve worked examples involving {title}."
            )

        if self._has_formula_like_content(content):
            objectives.append(
                f"Apply formulas and notation related to {title}."
            )

        return self._unique(objectives)

    def _difficulty(
        self,
        title: str,
        content: str,
        level: int,
    ) -> str:

        text = f"{title}\n{content}".lower()
        score = 0

        if level >= 3:
            score += 1

        if len(content) > 1200:
            score += 1

        if self._has_formula_like_content(content):
            score += 1

        if re.search(
            r"\b(proof|prove|theorem|inverse|determinant|"
            r"transformation|application|complex|advanced)\b",
            text,
        ):
            score += 1

        if score >= 3:
            return "hard"

        if score == 0:
            return "easy"

        return "medium"

    def _populate_related_concepts(
        self,
        concepts: list[Concept],
        sections,
    ) -> None:

        concepts_by_section: dict[str, list[Concept]] = {}

        for concept in concepts:
            concepts_by_section.setdefault(
                concept.section_id,
                [],
            ).append(concept)

        sections_by_id = {
            section.section_id: section
            for section in sections
        }

        for concept in concepts:
            related: list[str] = []
            section = sections_by_id.get(concept.section_id)

            if section is not None:
                related_section_ids = []

                if section.parent_section:
                    related_section_ids.append(section.parent_section)

                related_section_ids.extend(section.child_sections)

                if section.parent_section:
                    parent = sections_by_id.get(section.parent_section)

                    if parent is not None:
                        related_section_ids.extend(parent.child_sections)

                for section_id in related_section_ids:
                    for related_concept in concepts_by_section.get(
                        section_id,
                        [],
                    ):
                        if related_concept.concept_id != concept.concept_id:
                            related.append(related_concept.concept_id)

            concept_terms = self._concept_terms(concept)

            for other in concepts:
                if other.concept_id == concept.concept_id:
                    continue

                other_terms = self._concept_terms(other)

                if self._has_named_prerequisite(concept, other):
                    related.append(other.concept_id)
                    continue

                shared_terms = concept_terms & other_terms

                if len(shared_terms) >= 2:
                    related.append(other.concept_id)

            concept.related_concepts = self._unique(related)[:8]

    def _concept_terms(
        self,
        concept: Concept,
    ) -> set[str]:

        terms: set[str] = set()

        for value in [
            concept.title,
            *concept.aliases,
            *concept.keywords,
            *concept.prerequisites,
        ]:
            terms.update(
                self._term_tokens(value)
            )

        return terms

    def _has_named_prerequisite(
        self,
        concept: Concept,
        other: Concept,
    ) -> bool:

        prerequisite_terms = {
            self._normalize_relation_text(prerequisite)
            for prerequisite in concept.prerequisites
        }

        other_names = {
            self._normalize_relation_text(other.title),
            *(
                self._normalize_relation_text(alias)
                for alias in other.aliases
            ),
        }

        return bool(prerequisite_terms & other_names)

    def _formatted_terms(
        self,
        content: str,
    ) -> list[str]:

        terms: list[str] = []

        patterns = (
            r"\*\*([^*\n][^*\n]+?)\*\*",
            r"__([^_\n][^_\n]+?)__",
            r"(?<!\*)\*([^*\n][^*\n]+?)\*(?!\*)",
            r"(?<!_)_([^_\n][^_\n]+?)_(?!_)",
        )

        for pattern in patterns:
            terms.extend(
                re.findall(
                    pattern,
                    content,
                )
            )

        return terms

    def _math_identifiers(
        self,
        content: str,
    ) -> list[str]:

        identifiers: list[str] = []

        for expression in re.findall(r"\$([^$]+)\$", content):
            identifiers.extend(
                re.findall(
                    r"[A-Za-z][A-Za-z0-9_]*",
                    expression,
                )
            )

        identifiers.extend(
            re.findall(
                r"\b[A-Z](?:\^\{?\d+\}?|_\{?[A-Za-z0-9]+\}?)?\b",
                content,
            )
        )

        return identifiers

    def _has_formula_like_content(
        self,
        content: str,
    ) -> bool:

        return bool(
            re.search(
                r"(\$\$?.+?\$\$?|\\\(|\\\[|=|<=|>=|"
                r"\\leq?|\\geq?|\\frac|\\sqrt|\bsin\b|\bcos\b|\btan\b)",
                content,
                flags=re.DOTALL,
            )
        )

    def _repeated_terms(
        self,
        text: str,
    ) -> list[str]:

        words = [
            word.lower()
            for word in re.findall(
                r"[A-Za-z][A-Za-z0-9-]*",
                text,
            )
            if self._is_keyword_candidate(word)
        ]

        counts = Counter(words)

        return [
            word
            for word, count in counts.items()
            if count > 1
        ]

    def _paragraph_blocks(
        self,
        text: str,
        clean: bool = True,
    ) -> list[str]:

        source = text

        if clean:
            source = re.sub(
                r"<!--.*?-->",
                "",
                source,
                flags=re.DOTALL,
            )

            source = re.sub(
                r"={5,}",
                "",
                source,
            )

        return [
            block.strip()
            for block in re.split(
                r"\n\s*\n",
                source,
            )
            if block.strip()
        ]

    def _is_keyword_candidate(
        self,
        word: str,
    ) -> bool:

        normalized = word.lower()

        return (
            len(normalized) > 3
            and normalized not in self._STOPWORDS
        )

    def _is_heading(
        self,
        paragraph: str,
    ) -> bool:

        first_line = paragraph.strip().splitlines()[0].strip()

        return first_line.startswith("#")

    def _is_example(
        self,
        paragraph: str,
    ) -> bool:

        first_line = paragraph.strip().splitlines()[0].strip()

        return bool(self._EXAMPLE_PATTERN.match(first_line))

    @staticmethod
    def _is_noise(paragraph: str) -> bool:

        stripped = paragraph.strip()

        if not stripped:
            return True

        return bool(re.fullmatch(r"[-=_\s]+", stripped))

    def _normalize_term(
        self,
        term: str,
    ) -> str:

        term = self._clean_inline_markdown(term)

        term = re.split(
            r"[.;,\n:]",
            term,
            maxsplit=1,
        )[0]

        term = re.sub(
            r"\s+",
            " ",
            term,
        ).strip()

        term = term.strip("()[]{}")

        term = re.sub(
            r"^(?:the|a|an)\s+",
            "",
            term,
            flags=re.IGNORECASE,
        )

        if not term:
            return ""

        if term.lower() in self._STOPWORDS:
            return ""

        return term

    def _term_tokens(
        self,
        text: str,
    ) -> set[str]:

        return {
            token
            for token in re.findall(
                r"[A-Za-z][A-Za-z0-9-]*",
                text.lower(),
            )
            if self._is_keyword_candidate(token)
        }

    def _normalize_relation_text(
        self,
        text: str,
    ) -> str:

        return " ".join(
            sorted(
                self._term_tokens(text)
            )
        )

    @staticmethod
    def _clean_inline_markdown(text: str) -> str:

        cleaned = re.sub(
            r"`([^`]+)`",
            r"\1",
            text,
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

    @staticmethod
    def _unique(values) -> list[str]:

        seen: set[str] = set()

        unique_values: list[str] = []

        for value in values:
            if not value:
                continue

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)

            unique_values.append(value)

        return unique_values

    @staticmethod
    def _slug(text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9]+",
            "-",
            text,
        )

        return text.strip("-")
