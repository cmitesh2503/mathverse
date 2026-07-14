import sys
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "infrastructure"
    / "cloud_function_knowledge_compiler"
)

sys.path.insert(0, str(FUNCTION_DIR))

from figure_extractor import FigureExtractor
from firestore_writer import FirestoreWriter
from models import Chapter, Concept, Curriculum


def test_cloud_figure_extractor_extracts_figures_diagrams_and_images():
    chapter = Chapter(
        id="coordinate_geometry",
        name="Coordinate Geometry",
        order=1,
        concepts=[
            Concept(
                id="distance_formula",
                name="Distance Formula",
                chapter_id="coordinate_geometry",
                order=1,
            )
        ],
    )
    next_chapter = Chapter(
        id="limits",
        name="Limits",
        order=2,
    )
    document = """
# Coordinate Geometry

The Distance Formula diagram appears in Fig. 7.1.

![Fig. 7.2 Coordinate plane](images/fig7_2.png)

<figure>
<img src="images/fig7_3.svg" alt="Triangle ABC" />
<figcaption>Diagram 7.3 Triangle ABC.</figcaption>
</figure>

Fig. 7.1

# Limits

Fig. 8.1 belongs to the next chapter.
"""

    updated = FigureExtractor().extract(
        chapter,
        document,
        next_chapter=next_chapter,
    )

    assert [figure.id for figure in updated.figures] == [
        "coordinate_geometry_figure_001",
        "coordinate_geometry_figure_002",
        "coordinate_geometry_figure_003",
    ]

    first = updated.figures[0]
    assert first.reference == "Fig. 7.1"
    assert first.caption == "Fig. 7.1"
    assert first.image_ref == ""
    assert first.description == "The Distance Formula diagram appears in Fig. 7.1."
    assert first.figure_type == "diagram"
    assert first.concept_ids == ["distance_formula"]

    image = updated.figures[1]
    assert image.reference == "Fig. 7.2"
    assert image.caption == "Fig. 7.2 Coordinate plane"
    assert image.image_ref == "images/fig7_2.png"
    assert image.figure_type == "diagram"

    diagram = updated.figures[2]
    assert diagram.reference == "Diagram 7.3"
    assert diagram.caption == "Diagram 7.3 Triangle ABC."
    assert diagram.image_ref == "images/fig7_3.svg"
    assert diagram.figure_type == "diagram"


def test_cloud_firestore_writer_saves_figures_collection():
    curriculum = Curriculum(
        exam="JEE",
        subject="Mathematics",
        grade="11",
        chapters=[
            Chapter(
                id="coordinate_geometry",
                name="Coordinate Geometry",
                order=1,
            )
        ],
    )

    curriculum.chapters[0] = FigureExtractor().extract(
        curriculum.chapters[0],
        "Coordinate Geometry\n\n![Fig. 7.2 Coordinate plane](images/fig7_2.png)",
    )

    db = _FakeDb()
    writer = FirestoreWriter.__new__(FirestoreWriter)
    writer.db = db

    writer.save_figures(curriculum)

    assert db.batch_instance.committed
    assert db.batch_instance.writes == [
        (
            ("figures", "coordinate_geometry_figure_001"),
            {
                "id": "coordinate_geometry_figure_001",
                "chapter_id": "coordinate_geometry",
                "order": 1,
                "reference": "Fig. 7.2",
                "caption": "Fig. 7.2 Coordinate plane",
                "image_ref": "images/fig7_2.png",
                "image_path": "images/fig7_2.png",
                "description": "Fig. 7.2 Coordinate plane",
                "figure_type": "diagram",
                "concept_ids": [],
            },
        )
    ]


class _FakeDb:
    def __init__(self):
        self.batch_instance = _FakeBatch()

    def batch(self):
        return self.batch_instance

    def collection(self, name):
        return _FakeCollection((name,))


class _FakeCollection:
    def __init__(self, path):
        self.path = path

    def document(self, document_id):
        return _FakeDocument((*self.path, document_id))


class _FakeDocument:
    def __init__(self, path):
        self.path = path


class _FakeBatch:
    def __init__(self):
        self.writes = []
        self.committed = False

    def set(self, ref, payload):
        self.writes.append(
            (
                ref.path,
                payload,
            )
        )

    def commit(self):
        self.committed = True
