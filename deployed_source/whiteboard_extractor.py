from models import (
    ExtractionResult
)


class WhiteboardExtractor:

    """
    Generates whiteboard teaching steps.
    """

    def extract(
        self,
        teacher_scripts
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="whiteboards",
            metadata={},
            data={
                "whiteboards": []
            }
        )