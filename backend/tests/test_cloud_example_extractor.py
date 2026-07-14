import sys
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "infrastructure"
    / "cloud_function_knowledge_compiler"
)

sys.path.insert(0, str(FUNCTION_DIR))

from example_extractor import ExampleExtractor
from firestore_writer import FirestoreWriter
from models import Chapter, Concept, Curriculum


def test_cloud_example_extractor_extracts_supported_example_types():
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

Example 1: Find the distance between P(1, 2) and Q(4, 6).
Solution: Use the Distance Formula.
d = 5.

Worked Example 2
Problem: Find the midpoint of A(0, 0) and B(2, 4).
Sol. Midpoint = (1, 2).

Illustration 3
Question: Find the slope of the line.
Answer: Slope = 2.

Solved Example 4
Find the intercept.
Solution:
The intercept is 3.

## Exercise 1

Example 5: This should be skipped.
Solution: Exercise examples are not teaching examples.

# Limits

Example 6: This belongs to the next chapter.
Solution: Skip it.
"""

    updated = ExampleExtractor().extract(
        chapter,
        document,
        next_chapter=next_chapter,
    )

    assert [example.title for example in updated.examples] == [
        "Example 1",
        "Worked Example 2",
        "Illustration 3",
        "Solved Example 4",
    ]
    assert [example.id for example in updated.examples] == [
        "coordinate_geometry_example_001",
        "coordinate_geometry_example_002",
        "coordinate_geometry_example_003",
        "coordinate_geometry_example_004",
    ]

    first = updated.examples[0]
    assert first.problem == "Find the distance between P(1, 2) and Q(4, 6)."
    assert first.solution == "Use the Distance Formula.\nd = 5."
    assert first.difficulty == "Easy"
    assert first.concept_ids == ["distance_formula"]

    assert updated.examples[1].problem == "Find the midpoint of A(0, 0) and B(2, 4)."
    assert updated.examples[1].solution == "Midpoint = (1, 2)."
    assert updated.examples[2].problem == "Find the slope of the line."
    assert updated.examples[2].solution == "Slope = 2."
    assert updated.examples[3].problem == "Find the intercept."
    assert updated.examples[3].solution == "The intercept is 3."


def test_cloud_example_extractor_skips_incomplete_examples():
    chapter = Chapter(
        id="coordinate_geometry",
        name="Coordinate Geometry",
        order=1,
    )

    updated = ExampleExtractor().extract(
        chapter,
        "Coordinate Geometry\n\nExample 1: Find the distance.",
    )

    assert updated.examples == []


def test_cloud_firestore_writer_saves_examples_collection():
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

    curriculum.chapters[0] = ExampleExtractor().extract(
        curriculum.chapters[0],
        "Coordinate Geometry\n\nExample 1: Find x.\nSolution: x = 2.",
    )

    db = _FakeDb()
    writer = FirestoreWriter.__new__(FirestoreWriter)
    writer.db = db

    writer.save_examples(curriculum)

    assert db.batch_instance.committed
    assert db.batch_instance.writes == [
        (
            ("examples", "coordinate_geometry_example_001"),
            {
                "id": "coordinate_geometry_example_001",
                "chapter_id": "coordinate_geometry",
                "order": 1,
                "title": "Example 1",
                "problem": "Find x.",
                "solution": "x = 2.",
                "difficulty": "Easy",
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
