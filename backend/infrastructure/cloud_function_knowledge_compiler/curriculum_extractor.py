import json

from pydantic import ValidationError

from ai_gateway import (
    generate_structured_response
)

from models import (
    Chapter,
    Curriculum,
    CurriculumMetadata,
)


CURRICULUM_SCHEMA = CurriculumMetadata


class CurriculumExtractor:

    def extract(
        self,
        document_text: str
    ) -> Curriculum:

        prompt = f"""
You are an educational curriculum extraction engine.

Extract ONLY the curriculum metadata listed below.
Do NOT generate concepts, prerequisites, learning objectives, subtopics, explanations, or any other knowledge.
Do NOT invent or infer chapters.
Preserve chapter order exactly as it appears in the syllabus.
Keep the response small and return valid JSON only.

Output JSON must exactly match this structure:
{{
  "exam": "...",
  "subject": "...",
  "grade": "...",
  "chapters": [
    {{
      "id": "...",
      "name": "...",
      "order": 1
    }}
  ]
}}

Document

{document_text}
"""

        response = generate_structured_response(
            prompt,
            CURRICULUM_SCHEMA
        )

        if isinstance(response, dict) and isinstance(response.get("data"), dict):
            response = response["data"]

        if not isinstance(response, dict):
            raise ValueError(
                "Curriculum extraction returned non-dict output from the AI service."
            )

        try:
            validated = CURRICULUM_SCHEMA.parse_obj(response)
        except ValidationError as exc:
            raise ValueError(
                "Curriculum extraction failed schema validation. "
                f"Error: {exc}. Raw response: {response}"
            ) from exc

        chapters = [
            Chapter(id=chapter.id, name=chapter.name, order=chapter.order)
            for chapter in validated.chapters
        ]

        return Curriculum(
            exam=validated.exam,
            subject=validated.subject,
            grade=validated.grade,
            chapters=chapters
        )