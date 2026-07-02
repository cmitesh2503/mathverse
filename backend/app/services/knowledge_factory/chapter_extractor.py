from app.services.knowledge_factory.models import (
    ExtractionResult
)


class ChapterExtractor:
    """
    Extracts chapter information from a curriculum document.

    Responsibility
    --------------
    - Identify all chapters in the curriculum
    - Preserve chapter order
    - Generate chapter metadata

    Does NOT
    --------
    - Extract concepts
    - Extract formulas
    - Extract teacher scripts
    """

    def extract(
        self,
        curriculum
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="chapters",
            metadata={
                "source": "curriculum"
            },
            data={
                "chapters": []
            },
            warnings=[]
        )