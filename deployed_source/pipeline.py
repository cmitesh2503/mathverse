from curriculum_extractor import CurriculumExtractor
from concept_extractor import ConceptExtractor
from formula_extractor import FormulaExtractor
from example_extractor import ExampleExtractor
from exercise_extractor import ExerciseExtractor
from validator import Validator
from graph_builder import GraphBuilder
from firestore_writer import FirestoreWriter


class KnowledgePipeline:

    def __init__(self):

        self.curriculum = CurriculumExtractor()
        self.concepts = ConceptExtractor()
        self.formulas = FormulaExtractor()
        self.examples = ExampleExtractor()
        self.exercises = ExerciseExtractor()

        self.validator = Validator()
        self.graph = GraphBuilder()

        self.firestore = FirestoreWriter()

    def build_knowledge(
        self,
        document_text: str
    ):

        print("=" * 60)
        print("Knowledge Factory")
        print("=" * 60)

        curriculum = self.curriculum.extract(
            document_text
        )

        for index, chapter in enumerate(curriculum.chapters):

            updated = self.concepts.extract(
                chapter,
                document_text
            )

            chapter.concepts = updated.concepts

            next_chapter = None

            if index + 1 < len(curriculum.chapters):
                next_chapter = curriculum.chapters[index + 1]

            updated = self.formulas.extract(
                chapter,
                document_text,
                next_chapter=next_chapter,
            )

            chapter.formulas = updated.formulas

            updated = self.examples.extract(
                chapter,
                document_text,
                next_chapter=next_chapter,
            )

            chapter.examples = updated.examples

            updated = self.exercises.extract(
                chapter,
                document_text,
                next_chapter=next_chapter,
            )

            chapter.exercises = updated.exercises

        validation = self.validator.validate(
            curriculum
        )

        if not validation.valid:
            raise ValueError(validation.errors)

        self.firestore.save_curriculum(
            curriculum
        )

        self.firestore.save_chapters(
            curriculum
        )
        
        self.firestore.save_concepts(
            curriculum
        )

        self.firestore.save_formulas(
            curriculum
        )

        self.firestore.save_examples(
            curriculum
        )

        self.firestore.save_exercises(
            curriculum
        )

        graph = self.graph.build(
            curriculum
        )

        return graph
