"""
MathVerse Knowledge Factory

Chapter Firestore Writer

Responsible ONLY for persisting ChapterKnowledge
into Firestore.

No parsing logic belongs here.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from app.core.firestore_client import get_firestore_client
from app.services.knowledge_factory.chapter_models import ChapterKnowledge


class ChapterFirestoreWriter:
    """
    Writes ChapterKnowledge into Firestore.

    Firestore Structure

    curriculums/
        {curriculum_id}
            chapters/
                {chapter_id}
    """

    def __init__(self) -> None:
        self.db: firestore.Client = get_firestore_client()

    def save(self, chapter: ChapterKnowledge) -> str:
        """
        Persist one chapter.

        Returns
        -------
        curriculum_id
        """

        curriculum_ref = (
            self.db.collection("curriculums")
            .document(chapter.metadata.curriculum_id)
        )

        chapter_ref = (
            curriculum_ref
            .collection("chapters")
            .document(chapter.metadata.chapter_id)
        )

        metadata = asdict(chapter.metadata)

        metadata["created_at"] = datetime.now(timezone.utc)

        metadata["updated_at"] = datetime.now(timezone.utc)

        metadata["raw_markdown"] = chapter.raw_markdown

        metadata["section_count"] = len(chapter.sections)

        metadata["concept_count"] = len(chapter.concepts)

        metadata["formula_count"] = len(chapter.formulas)

        metadata["example_count"] = len(chapter.examples)

        chapter_ref.set(metadata)

        self._write_collection(
            chapter_ref,
            "sections",
            chapter.sections,
            "section_id",
        )

        self._write_collection(
            chapter_ref,
            "concepts",
            chapter.concepts,
            "concept_id",
        )

        self._write_collection(
            chapter_ref,
            "formulas",
            chapter.formulas,
            "formula_id",
        )

        self._write_collection(
            chapter_ref,
            "examples",
            chapter.examples,
            "example_id",
        )

        return chapter.metadata.curriculum_id

    def _write_collection(
        self,
        chapter_ref,
        collection_name: str,
        items: list,
        id_field: str,
    ) -> None:
        """
        Write a child collection.
        """

        if not items:
            return

        collection = chapter_ref.collection(collection_name)

        for item in items:
            document = asdict(item)

            document_id = document[id_field]
            if not document_id:
                raise ValueError(
                    f"{collection_name}: missing required field '{id_field}'"
                )

            collection.document(document_id).set(document)
