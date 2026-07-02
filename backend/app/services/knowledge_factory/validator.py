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
            errors.append("Exam missing.")

        if not curriculum.subject:
            errors.append("Subject missing.")

        if not curriculum.grade:
            errors.append("Grade missing.")

        if len(curriculum.chapters) == 0:
            errors.append("No chapters extracted.")

        for chapter in curriculum.chapters:

            if not chapter.name:
                errors.append(
                    "Chapter name missing."
                )

            for concept in chapter.concepts:

                if not concept.name:
                    errors.append(
                        f"Concept missing in {chapter.name}"
                    )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )