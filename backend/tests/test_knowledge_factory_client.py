from __future__ import annotations

from typing import Any

import pytest

from app.services.knowledge_factory.knowledge_factory_client import (
    KnowledgeFactoryClient,
    KnowledgeSearchResult,
)


class FakeSnapshot:
    def __init__(
        self,
        document_id: str,
        data: dict[str, Any],
    ) -> None:
        self.id = document_id
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return self._data


class FakeVectorQuery:
    def __init__(
        self,
        snapshots: list[FakeSnapshot],
    ) -> None:
        self.snapshots = snapshots
        self.stream_called = False
        self.where_calls: list[Any] = []

    def where(self, *, filter):
        self.where_calls.append(filter)
        return self

    def stream(self):
        self.stream_called = True
        return iter(self.snapshots)


class FakeCollection:
    def __init__(self) -> None:
        self.vector_query: FakeVectorQuery | None = None

    def find_nearest(
        self,
        *,
        vector_field: str,
        query_vector: list[float],
        distance_measure,
        limit: int,
        distance_result_field: str,
    ) -> FakeVectorQuery:

        assert vector_field == "embedding"

        assert query_vector == [
            0.1,
            0.2,
            0.3,
        ]

        assert limit == 5

        assert (
            distance_result_field
            == "vector_distance"
        )

        self.vector_query = FakeVectorQuery(
            [
                FakeSnapshot(
                    "vector-001",
                    {
                        "document_id": "doc-001",
                        "source_id": "concept-001",
                        "knowledge_type": "concept",
                        "text": (
                            "A matrix is a "
                            "rectangular array."
                        ),
                        "metadata": {
                            "section_number": "3.1",
                            "page": 10,
                        },
                        "vector_distance": 0.12,
                    },
                )
            ]
        )

        return self.vector_query


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.collections: dict[
            str,
            FakeCollection,
        ] = {}

    def collection(
        self,
        name: str,
    ) -> FakeCollection:

        if name not in self.collections:
            self.collections[name] = (
                FakeCollection()
            )

        return self.collections[name]


def create_client():
    firestore_client = (
        FakeFirestoreClient()
    )

    client = KnowledgeFactoryClient(
        project_id="knowledge-factory-prod",
        collection_name="knowledge_vectors",
        firestore_client=firestore_client,
    )

    return client, firestore_client


def test_client_uses_vector_collection():

    client, _ = create_client()

    assert (
        client.collection_name
        == "knowledge_vectors"
    )

    assert (
        client.project_id
        == "knowledge-factory-prod"
    )


def test_search_calls_firestore_vector_search():

    client, firestore_client = (
        create_client()
    )

    results = client.search(
        [
            0.1,
            0.2,
            0.3,
        ],
        top_k=5,
    )

    collection = (
        firestore_client.collections[
            "knowledge_vectors"
        ]
    )

    vector_query = collection.vector_query

    assert vector_query is not None
    assert vector_query.stream_called


def test_search_returns_provider_independent_results():

    client, _ = create_client()

    results = client.search(
        [
            0.1,
            0.2,
            0.3,
        ]
    )

    assert len(results) == 1

    result = results[0]

    assert isinstance(
        result,
        KnowledgeSearchResult,
    )

    assert (
        result.document_id
        == "doc-001"
    )

    assert (
        result.source_id
        == "concept-001"
    )

    assert (
        result.knowledge_type
        == "concept"
    )

    assert (
        result.text
        == "A matrix is a rectangular array."
    )

    assert result.distance == 0.12

    assert (
        result.metadata["section_number"]
        == "3.1"
    )

    assert result.metadata["page"] == 10


def test_search_rejects_empty_vector():

    client, _ = create_client()

    with pytest.raises(ValueError):

        client.search([])


def test_search_rejects_invalid_top_k():

    client, _ = create_client()

    with pytest.raises(ValueError):

        client.search(
            [0.1, 0.2, 0.3],
            top_k=0,
        )


def test_search_can_scope_to_document():

    client, firestore_client = (
        create_client()
    )

    results = client.search(
        [
            0.1,
            0.2,
            0.3,
        ],
        top_k=5,
        document_id="doc-001",
    )

    assert len(results) == 1

    collection = (
        firestore_client.collections[
            "knowledge_vectors"
        ]
    )

    vector_query = collection.vector_query

    assert vector_query is not None

    assert len(
        vector_query.where_calls
    ) == 1