from app.services.knowledge_factory.models import (
    ValidationResult
)


class Validator:

    def validate(
        self,
        extraction
    ) -> ValidationResult:

        return ValidationResult(
            valid=True
        )