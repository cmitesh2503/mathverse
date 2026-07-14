import sys
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "infrastructure"
    / "cloud_function_knowledge_compiler"
)

sys.path.insert(0, str(FUNCTION_DIR))

from formula_extractor import FormulaExtractor
from firestore_writer import FirestoreWriter
from models import Chapter, Concept, Curriculum


def test_cloud_formula_extractor_populates_formula_fields_and_skips_exercises():
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
    document = r"""
# Coordinate Geometry

The Distance Formula is:

$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

Area relation:

A = πr²

## Exercise 1

x + y = 10

# Limits

L = x + 1
"""

    updated = FormulaExtractor().extract(
        chapter,
        document,
        next_chapter=next_chapter,
    )

    assert [formula.id for formula in updated.formulas] == [
        "coordinate_geometry_formula_001",
        "coordinate_geometry_formula_002",
    ]
    assert updated.formulas[0].latex == (
        r"d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}"
    )
    assert updated.formulas[0].variables == [
        "d",
        "x_2",
        "x_1",
        "y_2",
        "y_1",
    ]
    assert updated.formulas[0].meaning == "The Distance Formula is:"
    assert updated.formulas[0].description == "The Distance Formula is"
    assert updated.formulas[0].concept_ids == ["distance_formula"]
    assert updated.formulas[1].latex == r"A = \pi r^2"
    assert updated.formulas[1].variables == ["A", "r"]


def test_cloud_firestore_writer_saves_formulas_collection():
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

    curriculum.chapters[0] = FormulaExtractor().extract(
        curriculum.chapters[0],
        "Coordinate Geometry\n\nArea relation:\n\nA = πr²",
    )

    db = _FakeDb()
    writer = FirestoreWriter.__new__(FirestoreWriter)
    writer.db = db

    writer.save_formulas(curriculum)

    assert db.batch_instance.committed
    assert db.batch_instance.writes == [
        (
            ("formulas", "coordinate_geometry_formula_001"),
            {
                "id": "coordinate_geometry_formula_001",
                "chapter_id": "coordinate_geometry",
                "order": 1,
                "latex": r"A = \pi r^2",
                "variables": ["A", "r"],
                "description": "Area relation",
                "meaning": "Area relation:",
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
