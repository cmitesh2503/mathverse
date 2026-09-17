from __future__ import annotations

import pytest

from app.services.knowledge_factory.knowledge_factory_client import (
    KnowledgeFactoryClient,
)


class Snapshot:
    def __init__(self, document_id: str, data: dict):
        self.id = document_id
        self._data = data
        self.exists = True

    def to_dict(self):
        return self._data


class Document:
    def __init__(self, snapshot: Snapshot | None):
        self.snapshot = snapshot

    def get(self):
        if self.snapshot is None:
            missing = Snapshot("missing", {})
            missing.exists = False
            return missing
        return self.snapshot


class Collection:
    def __init__(self, snapshots: list[Snapshot]):
        self.snapshots = snapshots

    def document(self, document_id: str):
        return Document(
            next(
                (item for item in self.snapshots if item.id == document_id),
                None,
            )
        )

    def stream(self):
        return iter(self.snapshots)


class Firestore:
    def __init__(self, snapshots: list[Snapshot]):
        self.collection_data = Collection(snapshots)

    def collection(self, name: str):
        assert name in {"knowledge_packages", "knowledge_vectors"}
        return self.collection_data


PACKAGE = {
    "schema_version": "1.0",
    "document_id": "doc-matrices-001",
    "metadata": {
        "subject": "Mathematics",
        "grade": "10",
        "board": "CBSE",
    },
    "chapters": [
        {"id": "chapter-003", "number": 3, "title": "Matrices"},
    ],
    "sections": [],
    "concepts": [],
    "formulas": [],
    "examples": [],
    "exercises": [],
    "figures": [],
    "tables": [],
}


def test_resolves_canonical_package_by_curriculum_and_chapter():
    client = KnowledgeFactoryClient(
        project_id="knowledge-factory-prod",
        collection_name="knowledge_vectors",
        firestore_client=Firestore([Snapshot("doc-matrices-001", PACKAGE)]),
    )

    result = client.resolve_package(
        subject="Mathematics",
        grade=10,
        board="CBSE",
        chapter="Matrices",
    )

    assert result == ("doc-matrices-001", PACKAGE)


def test_missing_package_returns_none():
    client = KnowledgeFactoryClient(
        project_id="knowledge-factory-prod",
        collection_name="knowledge_vectors",
        firestore_client=Firestore([]),
    )

    assert client.get_package("does-not-exist") is None


def test_firestore_failure_is_not_converted_to_local_fallback():
    class BrokenFirestore:
        def collection(self, _name):
            raise OSError("Firestore unavailable")

    with pytest.raises(OSError, match="Firestore unavailable"):
        KnowledgeFactoryClient(
            project_id="knowledge-factory-prod",
            collection_name="knowledge_vectors",
            firestore_client=BrokenFirestore(),
        )
