from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.services.ai_gateway import generate_structured_response
from app.services.knowledge_factory.knowledge_models import (
    Chapter,
    Concept,
    Curriculum,
    Definition,
    Example,
    ExerciseQuestion,
    Figure,
    Formula,
    KnowledgeDocument,
    LearningObjective,
    Metadata,
    Prerequisite,
    Property,
    Relationship,
    Section,
    Subsection,
    Table,
    Theorem,
)


METADATA_PROMPT = """
Extract only curriculum metadata from the markdown.
Return valid JSON with keys:
- curriculum_id
- title
- source
- publisher
- board
- grade
- subject
- language
- version
Keep values short. Use empty strings when unknown.
Do not extract chapters.

Markdown:
{markdown}
"""

OUTLINE_PROMPT = """
Extract only the chapter, section, and subsection outline from the markdown.
Return valid JSON as an array of chapters.
Each chapter must contain:
- id
- number
- title
- sections
Each section must contain:
- id
- number
- title
- subsections
Each subsection must contain:
- id
- number
- title
Do not include concepts, definitions, examples, properties, theorems, formulas, figures, tables, or exercises.

Markdown:
{markdown}
"""

CHAPTER_DETAILS_PROMPT = """
Extract only the learning content for the given chapter.
Return valid JSON with keys:
- subsections
- learning_objectives
- prerequisites
- relationships

Each subsection object must contain:
- id
- number
- title
- concepts
- definitions
- properties
- theorems
- formulas
- examples
- exercises
- figures
- tables

Do not repeat chapter or section headings.
Do not extract unrelated content.
Keep each array small and compact.

Chapter title:
{chapter_title}

Markdown:
{markdown}
"""


class KnowledgeBuilder:
    """Converts Azure Layout markdown into canonical knowledge.json."""

    def build(
        self,
        *,
        document_id: str,
        markdown: str,
        source: str = "Azure Document Intelligence",
    ) -> KnowledgeDocument:
        markdown = str(markdown or "").strip()
        if not markdown:
            raise RuntimeError("Markdown is empty.")

        metadata = self._extract_metadata(markdown=markdown, document_id=document_id)
        outline = self._extract_outline(markdown=markdown)
        chapter_details = self._extract_chapter_details(markdown=markdown, outline=outline)

        document = self._assemble_document(
            document_id=document_id,
            source=source,
            metadata=metadata,
            outline=outline,
            chapter_details=chapter_details,
        )
        return document

    def build_from_layout_json(
        self,
        *,
        layout_json_path: str | Path,
        document_id: str,
    ) -> KnowledgeDocument:
        markdown = self._extract_markdown(layout_json_path)
        return self.build(document_id=document_id, markdown=markdown)

    def save(self, knowledge: KnowledgeDocument, output_path: str | Path) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            knowledge.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    def _extract_markdown(self, layout_json_path: str | Path) -> str:
        layout_json_path = Path(layout_json_path)

        if not layout_json_path.exists():
            raise FileNotFoundError(layout_json_path)

        data = json.loads(layout_json_path.read_text(encoding="utf-8"))

        if isinstance(data.get("markdown"), str):
            return data["markdown"]

        if isinstance(data.get("content"), str):
            return data["content"]

        analyze = data.get("analyzeResult")
        if isinstance(analyze, dict):
            if isinstance(analyze.get("markdown"), str):
                return analyze["markdown"]
            if isinstance(analyze.get("content"), str):
                return analyze["content"]

        raise RuntimeError("Unable to locate markdown/content in layout.json.")

    def _extract_metadata(self, *, markdown: str, document_id: str) -> dict[str, Any]:
        response = generate_structured_response(
            prompt=METADATA_PROMPT.format(markdown=markdown[:2500]),
            response_schema=dict,
        )
        return self._safe_dict(
            response,
            default={
                "curriculum_id": document_id,
                "title": document_id,
                "source": "Azure Document Intelligence",
                "publisher": "",
                "board": "",
                "grade": "",
                "subject": "",
                "language": "",
                "version": "1.0",
            },
        )

    def _extract_outline(self, *, markdown: str) -> list[dict[str, Any]]:
        response = generate_structured_response(
            prompt=OUTLINE_PROMPT.format(markdown=markdown[:6000]),
            response_schema=list,
        )
        return self._safe_list(response)

    def _extract_chapter_details(
        self,
        *,
        markdown: str,
        outline: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        details: dict[str, dict[str, Any]] = {}
        for index, chapter in enumerate(outline, start=1):
            chapter_id = str(chapter.get("id") or f"chapter_{index}")
            chapter_title = str(chapter.get("title") or f"Chapter {index}")
            response = generate_structured_response(
                prompt=CHAPTER_DETAILS_PROMPT.format(
                    chapter_title=chapter_title,
                    markdown=markdown[:8000],
                ),
                response_schema=dict,
            )
            details[chapter_id] = self._safe_dict(
                response,
                default={
                    "subsections": chapter.get("sections") or [],
                    "learning_objectives": [],
                    "prerequisites": [],
                    "relationships": [],
                },
            )
        return details

    def _assemble_document(
        self,
        *,
        document_id: str,
        source: str,
        metadata: dict[str, Any],
        outline: list[dict[str, Any]],
        chapter_details: dict[str, dict[str, Any]],
    ) -> KnowledgeDocument:
        metadata_obj = Metadata(
            document_id=document_id,
            title=str(metadata.get("title") or document_id),
            source=str(metadata.get("source") or source),
            publisher=self._empty_to_none(metadata.get("publisher")),
            board=self._empty_to_none(metadata.get("board")),
            grade=self._empty_to_none(metadata.get("grade")),
            subject=self._empty_to_none(metadata.get("subject")),
            language=self._empty_to_none(metadata.get("language")),
            version=str(metadata.get("version") or "1.0"),
        )

        curriculum = Curriculum(
            id=str(metadata.get("curriculum_id") or document_id),
            title=str(metadata.get("title") or document_id),
        )

        document = KnowledgeDocument(
            metadata=metadata_obj,
            curriculum=curriculum,
            chapters=[],
            learning_objectives=[],
            prerequisites=[],
            relationships=[],
            extensions={},
        )

        for index, chapter in enumerate(outline, start=1):
            chapter_id = str(chapter.get("id") or f"chapter_{index}")
            chapter_obj = Chapter(
                id=chapter_id,
                number=self._empty_to_none(chapter.get("number")),
                title=str(chapter.get("title") or f"Chapter {index}"),
                sections=[],
            )

            chapter_payload = chapter_details.get(chapter_id, {})
            document.learning_objectives.extend(
                self._build_learning_objectives(chapter_payload.get("learning_objectives") or [])
            )
            document.prerequisites.extend(
                self._build_prerequisites(chapter_payload.get("prerequisites") or [])
            )
            document.relationships.extend(
                self._build_relationships(chapter_payload.get("relationships") or [])
            )

            subsections = chapter_payload.get("subsections") or chapter.get("sections") or []
            for section_index, section in enumerate(chapter.get("sections") or [], start=1):
                section_id = str(section.get("id") or f"{chapter_id}_section_{section_index}")
                section_obj = Section(
                    id=section_id,
                    number=self._empty_to_none(section.get("number")),
                    title=str(section.get("title") or f"Section {section_index}"),
                    subsections=[],
                )

                section_subsections = section.get("subsections") or []
                if not section_subsections and subsections:
                    section_subsections = subsections

                for subsection_index, subsection in enumerate(section_subsections, start=1):
                    subsection_obj = self._build_subsection(
                        subsection=subsection,
                        section_id=section_id,
                        subsection_index=subsection_index,
                    )
                    section_obj.subsections.append(subsection_obj)

                chapter_obj.sections.append(section_obj)

            document.chapters.append(chapter_obj)

        return document

    def _build_subsection(
        self,
        *,
        subsection: dict[str, Any],
        section_id: str,
        subsection_index: int,
    ) -> Subsection:
        subsection_id = str(subsection.get("id") or f"{section_id}_subsection_{subsection_index}")
        return Subsection(
            id=subsection_id,
            number=self._empty_to_none(subsection.get("number")),
            title=str(subsection.get("title") or f"Subsection {subsection_index}"),
            concepts=self._build_concepts(subsection.get("concepts") or []),
            definitions=self._build_definitions(subsection.get("definitions") or []),
            properties=self._build_properties(subsection.get("properties") or []),
            theorems=self._build_theorems(subsection.get("theorems") or []),
            formulas=self._build_formulas(subsection.get("formulas") or []),
            examples=self._build_examples(subsection.get("examples") or []),
            exercises=self._build_exercises(subsection.get("exercises") or []),
            figures=self._build_figures(subsection.get("figures") or []),
            tables=self._build_tables(subsection.get("tables") or []),
        )

    @staticmethod
    def _safe_dict(value: Any, default: dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                return default
        if isinstance(value, dict):
            return value
        return default

    @staticmethod
    def _safe_list(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _empty_to_none(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _build_learning_objectives(items: Iterable[dict[str, Any]]) -> list[LearningObjective]:
        results: list[LearningObjective] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                LearningObjective(
                    id=str(item.get("id") or f"lo_{index}"),
                    description=str(item.get("description") or item.get("text") or ""),
                )
            )
        return results

    @staticmethod
    def _build_prerequisites(items: Iterable[dict[str, Any]]) -> list[Prerequisite]:
        results: list[Prerequisite] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Prerequisite(
                    id=str(item.get("id") or f"pr_{index}"),
                    description=str(item.get("description") or item.get("text") or ""),
                )
            )
        return results

    @staticmethod
    def _build_relationships(items: Iterable[dict[str, Any]]) -> list[Relationship]:
        results: list[Relationship] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                Relationship(
                    source_id=str(item.get("source_id") or item.get("source") or ""),
                    target_id=str(item.get("target_id") or item.get("target") or ""),
                    relationship_type=str(item.get("relationship_type") or item.get("type") or "related_to"),
                )
            )
        return results

    @staticmethod
    def _build_concepts(items: Iterable[dict[str, Any]]) -> list[Concept]:
        results: list[Concept] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Concept(
                    id=str(item.get("id") or f"concept_{index}"),
                    title=str(item.get("title") or f"Concept {index}"),
                    explanation=str(item.get("explanation") or item.get("text") or ""),
                    definitions=[str(v) for v in item.get("definitions") or [] if str(v).strip()],
                    properties=[str(v) for v in item.get("properties") or [] if str(v).strip()],
                    theorems=[str(v) for v in item.get("theorems") or [] if str(v).strip()],
                    formulas=[str(v) for v in item.get("formulas") or [] if str(v).strip()],
                    examples=[str(v) for v in item.get("examples") or [] if str(v).strip()],
                    prerequisites=[str(v) for v in item.get("prerequisites") or [] if str(v).strip()],
                    related_concepts=[str(v) for v in item.get("related_concepts") or [] if str(v).strip()],
                )
            )
        return results

    @staticmethod
    def _build_definitions(items: Iterable[dict[str, Any]]) -> list[Definition]:
        results: list[Definition] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Definition(
                    id=str(item.get("id") or f"definition_{index}"),
                    title=str(item.get("title") or f"Definition {index}"),
                    text=str(item.get("text") or item.get("description") or ""),
                )
            )
        return results

    @staticmethod
    def _build_properties(items: Iterable[dict[str, Any]]) -> list[Property]:
        results: list[Property] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Property(
                    id=str(item.get("id") or f"property_{index}"),
                    title=str(item.get("title") or f"Property {index}"),
                    text=str(item.get("text") or item.get("description") or ""),
                )
            )
        return results

    @staticmethod
    def _build_theorems(items: Iterable[dict[str, Any]]) -> list[Theorem]:
        results: list[Theorem] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Theorem(
                    id=str(item.get("id") or f"theorem_{index}"),
                    title=str(item.get("title") or f"Theorem {index}"),
                    statement=str(item.get("statement") or item.get("text") or ""),
                    proof=str(item.get("proof") or "") or None,
                )
            )
        return results

    @staticmethod
    def _build_formulas(items: Iterable[dict[str, Any]]) -> list[Formula]:
        results: list[Formula] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Formula(
                    id=str(item.get("id") or f"formula_{index}"),
                    latex=str(item.get("latex") or item.get("text") or ""),
                    description=str(item.get("description") or "") or None,
                )
            )
        return results

    @staticmethod
    def _build_examples(items: Iterable[dict[str, Any]]) -> list[Example]:
        results: list[Example] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Example(
                    id=str(item.get("id") or f"example_{index}"),
                    title=str(item.get("title") or f"Example {index}"),
                    problem=str(item.get("problem") or item.get("text") or ""),
                    solution=str(item.get("solution") or "") or None,
                    example_type=str(item.get("example_type") or "") or None,
                )
            )
        return results

    @staticmethod
    def _build_exercises(items: Iterable[dict[str, Any]]) -> list[ExerciseQuestion]:
        results: list[ExerciseQuestion] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            marks = item.get("marks")
            results.append(
                ExerciseQuestion(
                    id=str(item.get("id") or f"exercise_{index}"),
                    number=str(item.get("number") or "") or None,
                    question=str(item.get("question") or item.get("text") or ""),
                    difficulty=str(item.get("difficulty") or "") or None,
                    marks=marks if isinstance(marks, int) else None,
                )
            )
        return results

    @staticmethod
    def _build_figures(items: Iterable[dict[str, Any]]) -> list[Figure]:
        results: list[Figure] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Figure(
                    id=str(item.get("id") or f"figure_{index}"),
                    title=str(item.get("title") or "") or None,
                    caption=str(item.get("caption") or "") or None,
                    image_reference=str(item.get("image_reference") or "") or None,
                )
            )
        return results

    @staticmethod
    def _build_tables(items: Iterable[dict[str, Any]]) -> list[Table]:
        results: list[Table] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                Table(
                    id=str(item.get("id") or f"table_{index}"),
                    title=str(item.get("title") or "") or None,
                    caption=str(item.get("caption") or "") or None,
                    markdown=str(item.get("markdown") or "") or None,
                )
            )
        return results
