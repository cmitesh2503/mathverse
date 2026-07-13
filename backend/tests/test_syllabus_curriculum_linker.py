import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
    Concept,
    Section,
)
from app.services.knowledge_factory.syllabus_curriculum_linker import (
    SyllabusCurriculumLinker,
)
from app.services.knowledge_factory.syllabus_models import (
    Syllabus,
    SyllabusChapter,
    SyllabusTopic,
)


class FakeSnapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = data
        self.reference = FakeDocumentRef(document_id, data)

    def to_dict(self):
        return {
            key: value
            for key, value in self._data.items()
            if not key.startswith("_")
        }


class FakeDocumentRef:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = data

    def collection(self, name):
        return FakeCollectionRef(
            self._data.setdefault(f"_{name}", {})
        )

    def set(self, payload, merge=False):
        if merge:
            self._data.update(payload)
            return
        self._data.clear()
        self._data.update(payload)


class FakeCollectionRef:
    def __init__(self, documents):
        self._documents = documents

    def document(self, document_id):
        return FakeDocumentRef(
            document_id,
            self._documents.setdefault(document_id, {}),
        )

    def stream(self):
        return [
            FakeSnapshot(document_id, data)
            for document_id, data in self._documents.items()
        ]


class FakeFirestore:
    def __init__(self, documents):
        self._documents = documents

    def collection(self, name):
        return FakeCollectionRef(
            self._documents.setdefault(name, {})
        )


def test_link_syllabus_maps_topics_to_curriculum_children():
    syllabus = Syllabus(
        syllabus_id="jee_jee-main_mathematics",
        board="jee",
        grade="jee-main",
        subject="Mathematics",
        version="2026",
        chapters=[
            SyllabusChapter(
                chapter_id="chapter-02",
                order=2,
                title="Matrices and Determinants",
                topics=[
                    SyllabusTopic(
                        topic_id="topic-001",
                        order=1,
                        title="Matrices",
                        subtopics=[
                            "Algebra of matrices",
                            "Inverse of a matrix",
                        ],
                    )
                ],
            )
        ],
    )
    db = FakeFirestore(
        {
            "curriculums": {
                "jee-main-2026-mathematics": {
                    "_chapters": {
                        "chapter-003": {
                            "chapter_id": "chapter-003",
                            "order": 3,
                            "title": "Matrices",
                            "slug": "matrices",
                            "_sections": {
                                "3-1-matrix": {
                                    "section_id": "3-1-matrix",
                                    "title": "Matrix",
                                    "concept_ids": ["matrix"],
                                },
                                "3-2-algebra-of-matrices": {
                                    "section_id": "3-2-algebra-of-matrices",
                                    "title": "Algebra of Matrices",
                                    "concept_ids": ["algebra-of-matrices"],
                                },
                                "3-3-inverse-of-a-matrix": {
                                    "section_id": "3-3-inverse-of-a-matrix",
                                    "title": "Inverse of a Matrix",
                                    "concept_ids": ["inverse-of-a-matrix"],
                                },
                            },
                            "_concepts": {
                                "matrix": {
                                    "concept_id": "matrix",
                                    "title": "Matrix",
                                    "section_id": "3-1-matrix",
                                },
                                "algebra-of-matrices": {
                                    "concept_id": "algebra-of-matrices",
                                    "title": "Algebra of Matrices",
                                    "section_id": "3-2-algebra-of-matrices",
                                },
                                "inverse-of-a-matrix": {
                                    "concept_id": "inverse-of-a-matrix",
                                    "title": "Inverse of a Matrix",
                                    "section_id": "3-3-inverse-of-a-matrix",
                                },
                            },
                        }
                    }
                }
            }
        }
    )

    SyllabusCurriculumLinker(db=db).link_syllabus(syllabus)

    topic = syllabus.chapters[0].topics[0]
    assert topic.curriculum_chapter_id == "chapter-003"
    assert topic.curriculum_section_ids == [
        "3-1-matrix",
        "3-2-algebra-of-matrices",
        "3-3-inverse-of-a-matrix",
    ]
    assert topic.curriculum_concept_ids == [
        "matrix",
        "algebra-of-matrices",
        "inverse-of-a-matrix",
    ]


def test_link_chapter_updates_existing_syllabus_topics():
    topic_document = {
        "topic_id": "topic-001",
        "order": 1,
        "title": "Matrices",
        "subtopics": ["Algebra of matrices"],
    }
    db = FakeFirestore(
        {
            "syllabuses": {
                "jee": {
                    "_grades": {
                        "jee-main": {
                            "_chapters": {
                                "chapter-02": {
                                    "chapter_id": "chapter-02",
                                    "order": 2,
                                    "title": "Matrices and Determinants",
                                    "_topics": {
                                        "topic-001": topic_document,
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    chapter = ChapterKnowledge(
        metadata=ChapterMetadata(
            chapter_id="chapter-003",
            curriculum_id="jee-main-2026-mathematics",
            order=3,
            title="Matrices",
            slug="matrices",
            exam="JEE Main",
            subject="Mathematics",
            grade="11",
            version="2026",
        ),
        sections=[
            Section(
                section_id="3-1-matrix",
                number="3.1",
                title="Matrix",
                level=2,
                content="A matrix is a rectangular arrangement.",
            )
        ],
        concepts=[
            Concept(
                concept_id="matrix",
                title="Matrix",
                section_id="3-1-matrix",
            )
        ],
    )

    linked_topics = SyllabusCurriculumLinker(db=db).link_chapter(chapter)

    assert linked_topics == 1
    assert topic_document["curriculum_chapter_id"] == "chapter-003"
    assert topic_document["curriculum_section_ids"] == ["3-1-matrix"]
    assert topic_document["curriculum_concept_ids"] == ["matrix"]
