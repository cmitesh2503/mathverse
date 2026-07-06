import json

from ai_gateway import (
    generate_structured_response
)

from models import (
    Curriculum,
    Chapter
)


CURRICULUM_SCHEMA = Curriculum


class CurriculumExtractor:

    def extract(
        self,
        document_text: str
    ) -> Curriculum:

        prompt = f"""
You are an educational curriculum extraction engine.

Extract ONLY:

- exam
- subject
- grade
- chapters

Return valid JSON.

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

        missing_fields = [
            field for field in ("exam", "subject", "grade")
            if not response.get(field)
        ]

        if missing_fields:
            raise ValueError(
                "Curriculum extraction failed: missing required fields: "
                f"{', '.join(missing_fields)}. "
                f"Raw response: {response}"
            )

        chapters = []

        raw_chapters = response.get("chapters", [])
        if raw_chapters is None:
            raw_chapters = []

        if not isinstance(raw_chapters, list):
            raise ValueError(
                "Curriculum extraction failed: `chapters` must be a list. "
                f"Raw response: {response}"
            )

        for idx, chapter in enumerate(raw_chapters):
            if not isinstance(chapter, dict) or "name" not in chapter:
                raise ValueError(
                    f"Curriculum extraction failed: each chapter must be an object "
                    f"with a `name` field. Raw chapter: {chapter}"
                )

            chapters.append(
                Chapter(
                    id=chapter["name"].lower().replace(" ", "_"),
                    name=chapter["name"],
                    order=idx + 1
                )
            )

        return Curriculum(
            exam=response.get("exam"),
            subject=response.get("subject"),
            grade=response.get("grade"),

            chapters=chapters
        )