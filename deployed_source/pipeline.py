from curriculum_extractor import CurriculumExtractor
from concept_extractor import ConceptExtractor
from validator import Validator
from graph_builder import GraphBuilder
from firestore_writer import FirestoreWriter


class KnowledgePipeline:

    def __init__(self):

        self.curriculum = CurriculumExtractor()
        self.concepts = ConceptExtractor()

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

        for chapter in curriculum.chapters:

            updated = self.concepts.extract(
                chapter,
                document_text
            )

            chapter.concepts = updated.concepts

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

        graph = self.graph.build(
            curriculum
        )

        return graph