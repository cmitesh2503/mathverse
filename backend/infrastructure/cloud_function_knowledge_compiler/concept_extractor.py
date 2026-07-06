from ai_gateway import (
    generate_structured_response
)

from models import (
    Concept
)


CONCEPT_SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    }
}


class ConceptExtractor:

    """
    Extract concepts from a single chapter.
    """

    def extract(
        self,
        chapter,
        document_text: str
    ):

        prompt = f"""
You are an expert JEE Mathematics curriculum designer.

Chapter

{chapter.name}

Document

{document_text}

Extract ONLY the major teachable concepts.

Return JSON.

Example

Matrices

↓

Definition

Order of Matrix

Types of Matrix

Matrix Equality

Matrix Addition

Matrix Multiplication

Transpose

Inverse

Properties
"""

        response = generate_structured_response(
            prompt,
            CONCEPT_SCHEMA
        )

        concepts = []

        for index, concept_name in enumerate(
            response.get(
                "concepts",
                []
            )
        ):

            concepts.append(

                Concept(

                    id=concept_name.lower().replace(
                        " ",
                        "_"
                    ),

                    name=concept_name,

                    chapter_id=chapter.id,

                    order=index + 1
                )
            )

        chapter.concepts = concepts

        return chapter