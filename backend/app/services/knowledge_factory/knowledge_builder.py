from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from app.ai.ai_gateway import generate_structured_response
from app.services.knowledge_factory.models import Chapter, Curriculum


class KnowledgeBuilderError(RuntimeError):
    pass


class KnowledgeBuilder:
    """Builds canonical chapter-level knowledge from Azure Layout output.

    This is intentionally conservative and compatible with the current
    repository model. It extracts curriculum metadata and chapter structure
    from Azure markdown, then serializes a normalized JSON artifact that can
    be extended later without changing the current importer contract.
    """

    def __init__(self) -> None:
        self._schema = {
            "type": "object",
            "properties": {
                "curriculum_id": {"type": "string"},
                "exam": {"type": "string"},
                "subject": {"type": "string"},
                "grade": {"type": "string"},
                "version": {"type": "string"},
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "order": {"type": "integer"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["id", "order", "title"],
                    },
                },
            },
            "required": ["curriculum_id", "exam", "subject", "grade", "version", "chapters"],
        }

    def build_from_layout_json(
        self,
        *,
        layout_json_path: str | Path,
        document_id: str,
    ) -> Curriculum:
        layout_json_path = Path(layout_json_path)
        if not layout_json_path.exists():
            raise FileNotFoundError(layout_json_path)

        layout_data = json.loads(layout_json_path.read_text(encoding="utf-8"))
        markdown = self._extract_markdown(layout_data)

        prompt = self._build_prompt(markdown=markdown, document_id=document_id)
        response = generate_structured_response(prompt=prompt, response_schema=self._schema)
        normalized = self._normalize_response(response, document_id=document_id)
        return self._to_curriculum(normalized)

    def save(self, curriculum: Curriculum, output_path: str | Path) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self._curriculum_to_dict(curriculum), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, knowledge_json_path: str | Path) -> Curriculum:
        knowledge_json_path = Path(knowledge_json_path)
        if not knowledge_json_path.exists():
            raise FileNotFoundError(knowledge_json_path)
        data = json.loads(knowledge_json_path.read_text(encoding="utf-8"))
        return self._to_curriculum(data)

    def _build_prompt(self, *, markdown: str, document_id: str) -> str:
        return (
            "You are MathVerse Knowledge Builder. Extract curriculum metadata and chapter structure from the markdown. "
            "Return ONLY valid JSON matching the schema. Do not invent information. Keep titles exactly as written. "
            f"Document ID: {document_id}\n\n"
            f"MARKDOWN:\n{markdown}"
        )

    def _extract_markdown(self, layout_data: dict[str, Any]) -> str:
        if isinstance(layout_data.get("markdown"), str):
            return layout_data["markdown"]
        if isinstance(layout_data.get("content"), str):
            return layout_data["content"]
        analyze = layout_data.get("analyzeResult")
        if isinstance(analyze, dict):
            if isinstance(analyze.get("markdown"), str):
                return analyze["markdown"]
            if isinstance(analyze.get("content"), str):
                return analyze["content"]
        raise KnowledgeBuilderError("Unable to locate markdown/content in layout.json")

    def _normalize_response(self, response: Any, *, document_id: str) -> dict[str, Any]:
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise KnowledgeBuilderError("KnowledgeBuilder response must be a JSON object")

        normalized = {
            "curriculum_id": str(response.get("curriculum_id") or document_id),
            "exam": str(response.get("exam") or ""),
            "subject": str(response.get("subject") or ""),
            "grade": str(response.get("grade") or ""),
            "version": str(response.get("version") or "1.0"),
            "chapters": [],
        }

        for index, chapter in enumerate(response.get("chapters") or [], start=1):
            if not isinstance(chapter, dict):
                continue
            normalized["chapters"].append(
                {
                    "id": str(chapter.get("id") or f"chapter_{index}"),
                    "order": int(chapter.get("order") or index),
                    "title": str(chapter.get("title") or ""),
                    "description": str(chapter.get("description") or ""),
                }
            )

        return normalized

    def _to_curriculum(self, data: dict[str, Any]) -> Curriculum:
        curriculum = Curriculum(
            curriculum_id=data["curriculum_id"],
            exam=data["exam"],
            subject=data["subject"],
            grade=data["grade"],
            version=data["version"],
        )
        curriculum.chapters = [
            Chapter(
                id=item["id"],
                order=item["order"],
                title=item["title"],
                description=item.get("description", ""),
            )
            for item in data.get("chapters", [])
        ]
        return curriculum

    def _curriculum_to_dict(self, curriculum: Curriculum) -> dict[str, Any]:
        payload = asdict(curriculum) if is_dataclass(curriculum) else dict(curriculum)
        payload["chapters"] = [asdict(chapter) if is_dataclass(chapter) else dict(chapter) for chapter in curriculum.chapters]
        return payload
