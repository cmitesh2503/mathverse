from firestore_client import (
    get_firestore_client
)


class FirestoreWriter:

    def __init__(self):

        self.db = get_firestore_client()

    def save_chapters(
        self,
        curriculum
    ):

        batch = self.db.batch()

        for chapter in curriculum.chapters:

            ref = (
                self.db
                .collection("chapters")
                .document(chapter.id)
            )

            batch.set(
                ref,
                chapter.model_dump()
            )

        batch.commit()
        
    def save_curriculum(
        self,
        curriculum
    ):

        self.db.collection(
            "curriculums"
        ).document(
            f"{curriculum.exam}_{curriculum.subject}_{curriculum.grade}"
        ).set(

            curriculum.model_dump()
        )
        
    def save_concepts(
        self,
        curriculum
    ):

        batch = self.db.batch()

        for chapter in curriculum.chapters:

            for concept in chapter.concepts:

                ref = (
                    self.db
                    .collection("concepts")
                    .document(concept.id)
                )

                batch.set(
                    ref,
                    concept.model_dump()
                )

        batch.commit()

        # Commit 5
        # Firestore persistence

    def save_formulas(
        self,
        curriculum
    ):

        batch = self.db.batch()

        writes = 0

        for chapter in curriculum.chapters:

            for formula in chapter.formulas:

                ref = (
                    self.db
                    .collection("formulas")
                    .document(formula.id)
                )

                batch.set(
                    ref,
                    formula.model_dump()
                )

                writes += 1

        if writes:

            batch.commit()

    def save_examples(
        self,
        curriculum
    ):

        batch = self.db.batch()

        writes = 0

        for chapter in curriculum.chapters:

            for example in chapter.examples:

                ref = (
                    self.db
                    .collection("examples")
                    .document(example.id)
                )

                batch.set(
                    ref,
                    example.model_dump()
                )

                writes += 1

        if writes:

            batch.commit()

    def save_exercises(
        self,
        curriculum
    ):

        batch = self.db.batch()

        writes = 0

        for chapter in curriculum.chapters:

            for exercise in chapter.exercises:

                ref = (
                    self.db
                    .collection("exercises")
                    .document(exercise.id)
                )

                batch.set(
                    ref,
                    exercise.model_dump()
                )

                writes += 1

        if writes:

            batch.commit()

    def save_figures(
        self,
        curriculum
    ):

        batch = self.db.batch()

        writes = 0

        for chapter in curriculum.chapters:

            for figure in chapter.figures:

                ref = (
                    self.db
                    .collection("figures")
                    .document(figure.id)
                )

                batch.set(
                    ref,
                    figure.model_dump()
                )

                writes += 1

        if writes:

            batch.commit()
