from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.services.ai_gateway import generate_structured_response
from app.services.knowledge_factory.knowledge_models import KnowledgeDocument


KNOWLEDGE_BUILDER_PROMPT = """
You are the MathVerse Knowledge Builder.

Your job is to convert Azure AI Document Intelligence Markdown
into the canonical KnowledgeDocument JSON.

Rules

1. Return ONLY valid JSON.
2. Never return markdown.
3. Never explain your reasoning.
4. Preserve hierarchy.
5. Detect:

- curriculum
- chapters
- sections
- subsections
- concepts
- definitions
- properties
- theorems
- formulas
- solved examples
- exercises
- figures
- tables
- learning objectives
- prerequisites
- relationships

6. Never invent information.
7. If information is missing return empty arrays.
8. Every id must be unique.
9. Every title must be preserved exactly.

Markdown

--------------------

{markdown}

--------------------
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
        prompt = KNOWLEDGE_BUILDER_PROMPT.format(markdown=markdown)

        response = generate_structured_response(
            prompt=prompt,
            response_schema=KnowledgeDocument,
        )

        if not response:
            raise RuntimeError("Gemini returned an empty KnowledgeDocument.")

        try:
            document = KnowledgeDocument.model_validate(response)
        except ValidationError as ex:
            raise RuntimeError(f"Invalid KnowledgeDocument generated.\n{ex}") from ex

        document.metadata.document_id = document_id
        document.metadata.source = source

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

    @staticmethod
    def load(knowledge_json_path: str | Path) -> KnowledgeDocument:
        knowledge_json_path = Path(knowledge_json_path)

        if not knowledge_json_path.exists():
            raise FileNotFoundError(knowledge_json_path)

        return KnowledgeDocument.model_validate_json(
            knowledge_json_path.read_text(encoding="utf-8")
        )

    @staticmethod
    def to_dict(knowledge: KnowledgeDocument) -> dict[str, Any]:
        return knowledge.model_dump(exclude_none=True)

    @staticmethod
    def to_json(knowledge: KnowledgeDocument) -> str:
        return knowledge.model_dump_json(indent=2, exclude_none=True)
