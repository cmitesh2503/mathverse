import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.chapter_models import (
    ChapterKnowledge,
    ChapterMetadata,
    Figure,
)
from app.services.knowledge_factory.chapter_firestore_writer import (
    ChapterFirestoreWriter,
)
from app.services.knowledge_factory.concept_extractor import ConceptExtractor
from app.services.knowledge_factory.figure_extractor import FigureExtractor
from app.services.knowledge_factory.section_parser import SectionParser


def _chapter(markdown: str) -> ChapterKnowledge:
    return ChapterKnowledge(
        metadata=ChapterMetadata(
            chapter_id="chapter-007",
            curriculum_id="jee-main-2026-mathematics",
            order=7,
            title="Coordinate Geometry",
            slug="coordinate-geometry",
            exam="JEE Main",
            subject="Mathematics",
            grade="11",
            version="2026",
        ),
        raw_markdown=markdown,
    )


def _extract(markdown: str) -> ChapterKnowledge:
    chapter = SectionParser().parse(
        _chapter(markdown)
    )
    chapter = ConceptExtractor().extract(chapter)
    return FigureExtractor().extract(chapter)


def test_figure_extractor_extracts_references_images_and_captions():
    chapter = _extract(
        """
# Coordinate Geometry

## 7.2 Distance Formula

The distance formula is shown in Fig. 7.1.

![Fig. 7.2 - Coordinate plane](images/fig7_2.png)

<figure>
<img src="images/diagram.svg" alt="Triangle ABC" />
<figcaption>Diagram 7.3 Triangle ABC with altitude AD.</figcaption>
</figure>

### 7.2.1 Graphs

Graph shown in Fig. 7.4.

## Exercise 7.2

1. Use Fig. 7.5 to answer the question.
"""
    )

    figures = {
        figure.figure_id: figure
        for figure in chapter.figures
    }
    sections = {
        section.section_id: section
        for section in chapter.sections
    }

    assert list(figures) == [
        "7-2-distance-formula-figure-001",
        "7-2-distance-formula-figure-002",
        "7-2-distance-formula-figure-003",
        "7-2-1-graphs-figure-001",
        "exercise-7-2-figure-001",
    ]

    first = figures["7-2-distance-formula-figure-001"]
    assert first.reference == "Fig. 7.1"
    assert first.caption == "Fig. 7.1"
    assert first.image_ref == ""
    assert first.description == "The distance formula is shown in Fig. 7.1."
    assert first.section_id == "7-2-distance-formula"
    assert first.chapter_id == "chapter-007"
    assert first.curriculum_id == "jee-main-2026-mathematics"

    image = figures["7-2-distance-formula-figure-002"]
    assert image.reference == "Fig. 7.2"
    assert image.caption == "Fig. 7.2 - Coordinate plane"
    assert image.image_ref == "images/fig7_2.png"
    assert image.image_path == "images/fig7_2.png"
    assert image.figure_type == "diagram"

    diagram = figures["7-2-distance-formula-figure-003"]
    assert diagram.reference == "Diagram 7.3"
    assert diagram.caption == "Diagram 7.3 Triangle ABC with altitude AD."
    assert diagram.image_ref == "images/diagram.svg"
    assert diagram.figure_type == "diagram"

    assert sections["7-2-distance-formula"].figure_ids == [
        "7-2-distance-formula-figure-001",
        "7-2-distance-formula-figure-002",
        "7-2-distance-formula-figure-003",
    ]
    assert sections["7-2-1-graphs"].figure_ids == [
        "7-2-1-graphs-figure-001",
    ]
    assert sections["exercise-7-2"].figure_ids == [
        "exercise-7-2-figure-001",
    ]


def test_chapter_firestore_writer_saves_figures_collection():
    chapter = _chapter("# Coordinate Geometry")
    chapter.figures = [
        Figure(
            figure_id="7-2-distance-formula-figure-001",
            reference="Fig. 7.1",
            caption="Fig. 7.1",
            image_ref="images/fig7_1.png",
            image_path="images/fig7_1.png",
            description="Distance formula diagram.",
            figure_type="diagram",
            section_id="7-2-distance-formula",
            chapter_id="chapter-007",
            curriculum_id="jee-main-2026-mathematics",
        )
    ]

    db = _FakeDb()
    writer = ChapterFirestoreWriter.__new__(ChapterFirestoreWriter)
    writer.db = db

    writer.save(chapter)

    metadata = next(
        payload
        for path, payload in db.writes
        if path == (
            "curriculums",
            "jee-main-2026-mathematics",
            "chapters",
            "chapter-007",
        )
    )
    assert metadata["figure_count"] == 1

    assert (
        (
            "curriculums",
            "jee-main-2026-mathematics",
            "chapters",
            "chapter-007",
            "figures",
            "7-2-distance-formula-figure-001",
        ),
        {
            "figure_id": "7-2-distance-formula-figure-001",
            "caption": "Fig. 7.1",
            "image_path": "images/fig7_1.png",
            "description": "Distance formula diagram.",
            "reference": "Fig. 7.1",
            "image_ref": "images/fig7_1.png",
            "figure_type": "diagram",
            "section_id": "7-2-distance-formula",
            "chapter_id": "chapter-007",
            "curriculum_id": "jee-main-2026-mathematics",
            "concept_ids": [],
        },
    ) in db.writes


class _FakeDb:
    def __init__(self):
        self.writes = []

    def collection(self, name):
        return _FakeCollection(
            (
                name,
            ),
            self.writes,
        )


class _FakeCollection:
    def __init__(self, path, writes):
        self.path = path
        self.writes = writes

    def document(self, document_id):
        return _FakeDocument(
            (
                *self.path,
                document_id,
            ),
            self.writes,
        )


class _FakeDocument:
    def __init__(self, path, writes):
        self.path = path
        self.writes = writes

    def collection(self, name):
        return _FakeCollection(
            (
                *self.path,
                name,
            ),
            self.writes,
        )

    def set(self, payload):
        self.writes.append(
            (
                self.path,
                payload,
            )
        )
