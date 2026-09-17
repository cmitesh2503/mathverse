from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import (
    DistanceMeasure,
)

from app.core import config

logger = logging.getLogger(__name__)


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
            else self._configured_firestore_client()
        )

        self.collection = self.client.collection(
            collection_name
        )

    def _configured_firestore_client(self) -> firestore.Client:
        from app.core.firestore_client import (
            get_knowledge_factory_firestore_client,
        )

        return get_knowledge_factory_firestore_client()

    def _log_read(self, collection_name: str, document_id: str | None = None) -> None:
        if config.APP_ENV.lower() in {"development", "dev", "test"}:
            logger.info(
                "Knowledge Factory read project=%s database=%s collection=%s document=%s source=firestore",
                self.project_id,
                config.KNOWLEDGE_FACTORY_DATABASE_ID,
                collection_name,
                document_id or "<query>",
            )

    @classmethod
    def from_config(
        cls,
        *,
        firestore_client: firestore.Client | None = None,
    ) -> "KnowledgeFactoryClient":
        """Build the read gateway from Knowledge Factory configuration."""

        project_id = config.KNOWLEDGE_FACTORY_PROJECT_ID.strip()
        if not project_id:
            raise RuntimeError(
                "KNOWLEDGE_FACTORY_PROJECT_ID is required; "
                "MathVerse will not use its application Firestore project "
                "as a knowledge-source fallback."
            )

        return cls(
            project_id=project_id,
            collection_name=config.KNOWLEDGE_FACTORY_VECTOR_COLLECTION,
            firestore_client=firestore_client,
        )

    def get_package(
        self,
        document_id: str,
        *,
        package_collection: str = config.KNOWLEDGE_FACTORY_PACKAGE_COLLECTION,
    ) -> dict[str, Any] | None:
        """Read one canonical Knowledge Factory package document."""

        normalized_id = str(document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id cannot be empty")

        self._log_read(package_collection, normalized_id)
        snapshot = (
            self.client.collection(package_collection)
            .document(normalized_id)
            .get()
        )
        if not snapshot.exists:
            return None

        data = snapshot.to_dict() or {}
        if not isinstance(data, dict):
            raise RuntimeError(
                f"Knowledge Factory document {normalized_id!r} "
                "does not contain an object payload."
            )
        return data

    def resolve_package(
        self,
        *,
        subject: str,
        grade: str | int,
        board: str,
        chapter: str,
        topic_id: str | None = None,
        package_collection: str = config.KNOWLEDGE_FACTORY_PACKAGE_COLLECTION,
    ) -> tuple[str, dict[str, Any]] | None:
        """Resolve a package using only canonical package data and identity."""

        expected = {
            "subject": self._normalise(subject),
            "grade": self._normalise(grade),
            "board": self._normalise(board),
        }
        chapter_value = self._normalise(chapter)
        topic_value = self._normalise(topic_id)

        self._log_read(package_collection)

        for snapshot in self.client.collection(package_collection).stream():
            data = snapshot.to_dict() or {}
            if not isinstance(data, dict):
                continue

            metadata = data.get("metadata")
            if not isinstance(metadata, dict):
                continue
            if any(
                self._normalise(metadata.get(key)) != value
                for key, value in expected.items()
            ):
                continue

            chapters = data.get("chapters")
            if not isinstance(chapters, list):
                continue
            matching_chapter = next(
                (
                    item
                    for item in chapters
                    if isinstance(item, dict)
                    and self._chapter_matches(item, chapter_value, topic_value)
                ),
                None,
            )
            if matching_chapter is not None:
                return str(data.get("document_id") or snapshot.id), data

        return None

    def list_packages(
        self,
        *,
        package_collection: str = config.KNOWLEDGE_FACTORY_PACKAGE_COLLECTION,
    ) -> list[tuple[str, dict[str, Any]]]:
        """List canonical package documents for identity resolution."""

        self._log_read(package_collection)
        packages: list[tuple[str, dict[str, Any]]] = []
        for snapshot in self.client.collection(package_collection).stream():
            data = snapshot.to_dict() or {}
            if isinstance(data, dict):
                packages.append((str(data.get("document_id") or snapshot.id), data))
        return packages

    @staticmethod
    def _normalise(value: object) -> str:
        return " ".join(str(value or "").strip().lower().replace("_", " ").split())

    @classmethod
    def _chapter_matches(
        cls,
        chapter: dict[str, Any],
        chapter_value: str,
        topic_value: str,
    ) -> bool:
        values = {
            cls._normalise(chapter.get("id")),
            cls._normalise(chapter.get("title")),
            cls._normalise(chapter.get("number")),
        }
        return chapter_value in values or bool(topic_value and topic_value in values)

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