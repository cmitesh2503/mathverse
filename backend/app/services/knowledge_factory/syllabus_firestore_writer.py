from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from app.core.firestore_client import get_firestore_client
from app.services.knowledge_factory.syllabus_models import Syllabus


class SyllabusFirestoreWriter:
    """
    Writes syllabus structure into:

    syllabuses/{board}/grades/{grade}/chapters/{chapter_id}/topics/{topic_id}
    """

    def __init__(self) -> None:
        self.db = get_firestore_client()

    def save(self, syllabus: Syllabus) -> str:
        updated_at = datetime.now(timezone.utc)
        board_ref = self.db.collection("syllabuses").document(syllabus.board)
        grade_ref = board_ref.collection("grades").document(syllabus.grade)

        board_ref.set(
            {
                "board": syllabus.board,
                "updated_at": updated_at,
            },
            merge=True,
        )

        topic_count = sum(len(chapter.topics) for chapter in syllabus.chapters)
        grade_ref.set(
            {
                "syllabus_id": syllabus.syllabus_id,
                "board": syllabus.board,
                "grade": syllabus.grade,
                "subject": syllabus.subject,
                "version": syllabus.version,
                "source_path": syllabus.source_path,
                "chapter_count": len(syllabus.chapters),
                "topic_count": topic_count,
                "metadata": {
                    "board": syllabus.board,
                    "grade": syllabus.grade,
                    "subject": syllabus.subject,
                    "version": syllabus.version,
                    "source_path": syllabus.source_path,
                },
                "created_at": syllabus.created_at,
                "updated_at": updated_at,
            },
            merge=True,
        )

        batch = self.db.batch()
        pending_writes = 0

        for chapter in syllabus.chapters:
            chapter_ref = grade_ref.collection("chapters").document(chapter.chapter_id)
            batch.set(
                chapter_ref,
                {
                    "chapter_id": chapter.chapter_id,
                    "order": chapter.order,
                    "title": chapter.title,
                    "topic_count": len(chapter.topics),
                    "updated_at": updated_at,
                },
                merge=True,
            )
            pending_writes += 1

            for topic in chapter.topics:
                topic_ref = chapter_ref.collection("topics").document(topic.topic_id)
                payload = asdict(topic)
                payload["updated_at"] = updated_at
                batch.set(topic_ref, payload, merge=True)
                pending_writes += 1

            if pending_writes >= 400:
                batch.commit()
                batch = self.db.batch()
                pending_writes = 0

        if pending_writes:
            batch.commit()

        return syllabus.syllabus_id
