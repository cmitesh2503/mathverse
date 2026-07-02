from app.services.knowledge_factory.models import (
    ValidationResult
)


class Validator:

    def validate(
        self,
        curriculum
    ):

        errors = []

        if not curriculum.exam:

            errors.append(
                "Exam missing."
            )

        if not curriculum.subject:

            errors.append(
                "Subject missing."
            )

        if not curriculum.grade:

            errors.append(
                "Grade missing."
            )

        if len(
            curriculum.chapters
        ) == 0:

            errors.append(
                "No chapters extracted."
            )

        return ValidationResult(

            valid=len(errors) == 0,

            errors=errors
        )