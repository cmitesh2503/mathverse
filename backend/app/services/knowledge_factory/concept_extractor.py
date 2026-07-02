from app.services.knowledge_factory.models import (
    ExtractionResult
)


class ConceptExtractor:

    """
    Extracts chapter concepts from structured educational content.
    """

    def extract(
        self,
        curriculum
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="concepts",
            metadata={
                "source": "curriculum"
            },
            data={
                "concepts": []
            }
        )