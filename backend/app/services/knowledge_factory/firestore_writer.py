from app.core.firestore_client import (
    get_firestore_client
)


class FirestoreWriter:

    def __init__(self):

        self.db = get_firestore_client()

    def save(
        self,
        extraction
    ):

        print(
            "Knowledge ready for Firestore"
        )
        
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

        # Commit 5
        # Firestore persistence