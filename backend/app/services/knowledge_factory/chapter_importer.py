from __future__ import annotations

from pathlib import Path

from app.services.knowledge_factory.chapter_pipeline import ChapterPipeline
from app.services.knowledge_factory.chapter_parser import ChapterParser
from app.services.knowledge_factory.section_parser import SectionParser
from app.services.knowledge_factory.chapter_firestore_writer import (
    ChapterFirestoreWriter,
)
from app.services.knowledge_factory.concept_extractor import (
    ConceptExtractor,
)



class ChapterImporter:
    """
    Orchestrates importing a chapter PDF into Firestore.

    Responsibilities
    ----------------
    1. Run the PDF-to-merged-markdown pipeline
    2. Parse chapter metadata
    3. Parse sections
    4. Extract concepts
    5. Persist chapter knowledge
    """

    def __init__(self) -> None:

        self.pipeline = ChapterPipeline()

        self.parser = ChapterParser()

        self.section_parser = SectionParser()

        self.concept_extractor = ConceptExtractor()

        self.writer = ChapterFirestoreWriter()
        
    def import_pdf(
        self,
        pdf_file: str | Path,
        output_root: str | Path | None = None,
    ) -> str:

        print("=" * 80)
        print("MathVerse PDF Import")
        print("=" * 80)

        #
        # PDF
        # ↓
        # Azure Layout
        # ↓
        # Merged Markdown
        #

        pipeline = self.pipeline.process(
            pdf_file,
            output_root=output_root,
        )


        #
        # Markdown
        # ↓
        # Chapter
        #

        chapter = self.parser.parse(
            pipeline.merged_markdown_file
        )

        print("Chapter parsed")


        #
        # Sections
        #

        chapter = self.section_parser.parse(
            chapter
        )

        print()

        print(
            f"Sections extracted: {len(chapter.sections)}"
        )

        #
        # Concepts
        #

        chapter = self.concept_extractor.extract(
            chapter
        )

        print()

        print(
            f"Concepts extracted: {len(chapter.concepts)}"
        )

        #
        # Save
        #

        curriculum_id = self.writer.save(
            chapter
        )

        print()

        print("Firestore write completed.")

        return curriculum_id
