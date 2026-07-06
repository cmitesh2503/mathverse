from models import (
    ExtractionResult
)


class FormulaExtractor:

    """
    Extracts mathematical formulas.
    """

    def extract(
        self,
        concepts
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="formulas",
            metadata={},
            data={
                "formulas": []
            }
        )