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