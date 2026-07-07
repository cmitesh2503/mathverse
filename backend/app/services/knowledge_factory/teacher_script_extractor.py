from app.services.knowledge_factory.models import (
    ExtractionResult
)


class TeacherScriptExtractor:

    """
    Generates teacher scripts for each concept.
    """

    def extract(
        self,
        concepts
    ) -> ExtractionResult:

        return ExtractionResult(
            success=True,
            document_type="teacher_scripts",
            metadata={},
            data={
                "teacher_scripts": []
            }
        )