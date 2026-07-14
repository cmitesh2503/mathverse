from models import (
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

            for formula in chapter.formulas:

                if not formula.latex:
                    errors.append(
                        f"Formula latex missing in {chapter.name}"
                    )

                if not formula.chapter_id:
                    errors.append(
                        f"Formula chapter_id missing in {chapter.name}"
                    )

            for example in chapter.examples:

                if not example.problem:
                    errors.append(
                        f"Example problem missing in {chapter.name}"
                    )

                if not example.solution:
                    errors.append(
                        f"Example solution missing in {chapter.name}"
                    )

                if not example.chapter_id:
                    errors.append(
                        f"Example chapter_id missing in {chapter.name}"
                    )

            for exercise in chapter.exercises:

                if not exercise.question:
                    errors.append(
                        f"Exercise question missing in {chapter.name}"
                    )

                if not exercise.chapter_id:
                    errors.append(
                        f"Exercise chapter_id missing in {chapter.name}"
                    )

            for figure in chapter.figures:

                if not figure.chapter_id:
                    errors.append(
                        f"Figure chapter_id missing in {chapter.name}"
                    )

                if not figure.caption and not figure.reference:
                    errors.append(
                        f"Figure caption/reference missing in {chapter.name}"
                    )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
