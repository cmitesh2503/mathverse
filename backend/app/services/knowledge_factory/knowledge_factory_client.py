from __future__ import annotations

from typing import Any

from google.cloud import firestore


class KnowledgeFactoryClient:
    """
    Read-only client for consuming Knowledge Factory
    published knowledge.

    MathVerse must use this client instead of accessing
    Knowledge Factory persistence directly.
    """

    def __init__(
        self,
        project_id: str,
        collection_name: str = "knowledge_packages",
        client: firestore.Client | None = None,
    ) -> None:
        self.project_id = project_id
        self.collection_name = collection_name

        self.client = (
            client
            if client is not None
            else firestore.Client(
                project=project_id
            )
        )

        self.collection = self.client.collection(
            collection_name
        )

    def get_knowledge_package(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        """
        Read a published KnowledgePackage.

        This client intentionally provides no save,
        update, or delete operations.
        """

        if not document_id:
            raise ValueError(
                "document_id cannot be empty"
            )

        snapshot = (
            self.collection
            .document(document_id)
            .get()
        )

        if not snapshot.exists:
            return None

        return snapshot.to_dict()