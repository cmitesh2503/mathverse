import json

from app.services.ai_gateway import (
    generate_structured_response
)

from app.services.knowledge_factory.models import (
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

        chapters = []

        for idx, chapter in enumerate(
            response.get(
                "chapters",
                []
            )
        ):

            chapters.append(

                Chapter(

                    id=chapter["name"].lower().replace(
                        " ",
                        "_"
                    ),

                    name=chapter["name"],

                    order=idx + 1
                )
            )

        return Curriculum(

            exam=response["exam"],

            subject=response["subject"],

            grade=response["grade"],

            chapters=chapters
        )