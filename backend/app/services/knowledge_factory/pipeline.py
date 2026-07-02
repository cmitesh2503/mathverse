from app.services.knowledge_factory.curriculum_extractor import (
    CurriculumExtractor
)

from app.services.knowledge_factory.validator import (
    Validator
)

from app.services.knowledge_factory.graph_builder import (
    GraphBuilder
)

from app.services.knowledge_factory.firestore_writer import (
    FirestoreWriter
)

from app.services.knowledge_factory.chapter_extractor import (
    ChapterExtractor
)


class KnowledgePipeline:

    def __init__(self):

        self.curriculum = CurriculumExtractor()

        self.validator = Validator()
        
        self.firestore.save_curriculum(
            curriculum
        )

        self.graph = GraphBuilder()

        self.firestore = FirestoreWriter()
        
        self.chapter = ChapterExtractor()

    def process_pdf(
        self,
        bucket_name: str,
        blob_name: str
    ):

        print("=" * 60)
        print("Knowledge Factory")
        print(blob_name)
        print("=" * 60)

        curriculum = self.curriculum.extract(
            bucket_name,
            blob_name
        )
        
        chapters = self.chapter.extract(
            curriculum
        )

        validation = self.validator.validate(
            chapters
        )

        if not validation.valid:

            raise ValueError(
                validation.errors
            )

        graph = self.graph.build(
            curriculum
        )

        self.firestore.save(
            curriculum
        )

        return graph