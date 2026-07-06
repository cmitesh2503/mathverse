from backend.app.services.knowledge_factory.models import (
    ExtractionResult
)


class CheatSheetExtractor:

    """
    Generates revision cheat sheets.
    """

    def extract(
        self,
        chapter
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="cheatsheet",
            metadata={},
            data={
                "cheatsheet": {}
            }
        )