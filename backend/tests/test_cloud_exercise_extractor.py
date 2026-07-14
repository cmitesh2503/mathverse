import sys
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "infrastructure"
    / "cloud_function_knowledge_compiler"
)

sys.path.insert(0, str(FUNCTION_DIR))

from exercise_extractor import ExerciseExtractor
from firestore_writer import FirestoreWriter
from models import Chapter, Concept, Curriculum


def test_cloud_exercise_extractor_extracts_exercise_practice_mcq_and_numerical():
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

## Exercise 1.1
1. Find the distance using Distance Formula between A(0, 0) and B(3, 4). [2 marks]
2. Prove that the given points are collinear.

Practice
1. Solve x + 2 = 5.

MCQs
1. Which point lies on the x-axis?
A. (0, 2)
B. (2, 0)
C. (2, 2)
D. (1, 1)
Answer: B

Numericals
1. Calculate the area when r = 7.

Questions
Question 1: Explain the coordinate plane.

# Limits

Exercise 2.1
1. This belongs to the next chapter.
"""

    updated = ExerciseExtractor().extract(
        chapter,
        document,
        next_chapter=next_chapter,
    )

    assert [exercise.id for exercise in updated.exercises] == [
        "coordinate_geometry_exercise_001",
        "coordinate_geometry_exercise_002",
        "coordinate_geometry_exercise_003",
        "coordinate_geometry_exercise_004",
        "coordinate_geometry_exercise_005",
        "coordinate_geometry_exercise_006",
    ]

    assert updated.exercises[0].source == "Exercise 1.1"
    assert updated.exercises[0].title == "Exercise 1.1 Question 1"
    assert updated.exercises[0].question == (
        "Find the distance using Distance Formula between A(0, 0) and B(3, 4)."
    )
    assert updated.exercises[0].question_type == "numerical"
    assert updated.exercises[0].marks == 2
    assert updated.exercises[0].concept_ids == ["distance_formula"]

    assert updated.exercises[2].source == "Practice"
    assert updated.exercises[2].question_type == "numerical"
    assert updated.exercises[2].question == "Solve x + 2 = 5."

    mcq = updated.exercises[3]
    assert mcq.source == "MCQs"
    assert mcq.question_type == "mcq"
    assert mcq.question == "Which point lies on the x-axis?"
    assert mcq.options == [
        "A. (0, 2)",
        "B. (2, 0)",
        "C. (2, 2)",
        "D. (1, 1)",
    ]
    assert mcq.answer == "B"

    assert updated.exercises[4].source == "Numericals"
    assert updated.exercises[4].question_type == "numerical"
    assert updated.exercises[5].source == "Questions"
    assert updated.exercises[5].question_type == "question"


def test_cloud_exercise_extractor_extracts_single_inline_practice_question():
    chapter = Chapter(
        id="linear_equations",
        name="Linear Equations",
        order=1,
    )

    updated = ExerciseExtractor().extract(
        chapter,
        "Linear Equations\n\nPractice: Solve 2x = 8.",
    )

    assert len(updated.exercises) == 1
    assert updated.exercises[0].question == "Solve 2x = 8."
    assert updated.exercises[0].question_type == "numerical"


def test_cloud_firestore_writer_saves_exercises_collection():
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

    curriculum.chapters[0] = ExerciseExtractor().extract(
        curriculum.chapters[0],
        "Coordinate Geometry\n\nExercise 1.1\n1. Find x if x + 1 = 3.",
    )

    db = _FakeDb()
    writer = FirestoreWriter.__new__(FirestoreWriter)
    writer.db = db

    writer.save_exercises(curriculum)

    assert db.batch_instance.committed
    assert db.batch_instance.writes == [
        (
            ("exercises", "coordinate_geometry_exercise_001"),
            {
                "id": "coordinate_geometry_exercise_001",
                "chapter_id": "coordinate_geometry",
                "order": 1,
                "title": "Exercise 1.1 Question 1",
                "source": "Exercise 1.1",
                "question": "Find x if x + 1 = 3.",
                "question_type": "numerical",
                "options": [],
                "answer": "",
                "marks": None,
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
