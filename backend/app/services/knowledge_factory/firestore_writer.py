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

        # Commit 5
        # Firestore persistence