from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import (
    DistanceMeasure,
)


@dataclass(slots=True)
class KnowledgeSearchResult:
    """
    MathVerse-side, provider-independent knowledge result.
    """

    document_id: str
    source_id: str
    knowledge_type: str
    text: str
    distance: float | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class KnowledgeFactoryClient:
    """
    Read-only gateway from MathVerse to the
    Knowledge Factory published knowledge.

    This client must never write to Knowledge Factory.
    """

    def __init__(
        self,
        *,
        project_id: str,
        collection_name: str,
        firestore_client: firestore.Client | None = None,
    ) -> None:

        if not project_id:
            raise ValueError(
                "project_id cannot be empty"
            )

        if not collection_name:
            raise ValueError(
                "collection_name cannot be empty"
            )

        self.project_id = project_id
        self.collection_name = (
            collection_name
        )

        self.client = (
            firestore_client
            if firestore_client is not None
            else firestore.Client(
                project=project_id
            )
        )

        self.collection = self.client.collection(
            collection_name
        )

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[KnowledgeSearchResult]:
        """
        Read relevant knowledge from Firestore
        Vector Search.

        MathVerse provides the query embedding.
        Knowledge Factory only provides retrieval.
        """

        if not query_vector:
            raise ValueError(
                "query_vector cannot be empty"
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than zero"
            )

        vector_query = (
            self.collection.find_nearest(
                vector_field="embedding",
                query_vector=query_vector,
                distance_measure=(
                    DistanceMeasure.COSINE
                ),
                limit=top_k,
                distance_result_field=(
                    "vector_distance"
                ),
            )
        )

        if document_id:
            vector_query = (
                vector_query.where(
                    filter=firestore.FieldFilter(
                        "document_id",
                        "==",
                        document_id,
                    )
                )
            )

        results: list[
            KnowledgeSearchResult
        ] = []

        for snapshot in (
            vector_query.stream()
        ):

            data = snapshot.to_dict() or {}

            results.append(
                KnowledgeSearchResult(
                    document_id=data.get(
                        "document_id",
                        "",
                    ),
                    source_id=data.get(
                        "source_id",
                        "",
                    ),
                    knowledge_type=data.get(
                        "knowledge_type",
                        "",
                    ),
                    text=data.get(
                        "text",
                        "",
                    ),
                    distance=data.get(
                        "vector_distance"
                    ),
                    metadata=data.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return results