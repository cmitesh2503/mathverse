from __future__ import annotations

from pathlib import Path

from app.services.knowledge_factory.chapter_parser import ChapterParser
from app.services.knowledge_factory.chapter_firestore_writer import (
    ChapterFirestoreWriter,
)
from app.services.knowledge_factory.concept_extractor import (
    ConceptExtractor,
)
from app.services.knowledge_factory.section_parser import (
    SectionParser,
)


class ChapterImporter:
    """
    Orchestrates importing an Azure Document Intelligence
    chapter JSON into Firestore.

    Responsibilities
    ----------------
    1. Load Azure JSON
    2. Parse chapter
    3. Persist chapter
    """

    def __init__(self) -> None:
        self.parser = ChapterParser()
        self.section_parser = SectionParser()
        self.writer = ChapterFirestoreWriter()
        self.concept_extractor = ConceptExtractor()

    def import_json(self, json_file: str | Path) -> str:
        """
        Import a chapter from Azure JSON.

        Parameters
        ----------
        json_file:
            Path to Azure Layout JSON.

        Returns
        -------
        curriculum_id
        """

        json_file = Path(json_file)

        if not json_file.exists():
            raise FileNotFoundError(json_file)

        print("=" * 80)
        print("MathVerse Chapter Import")
        print("=" * 80)

        print(f"Loading : {json_file.name}")
        
        # Parse Azure Layout JSON
        
        chapter = self.parser.parse(json_file)
        chapter = self.section_parser.parse(chapter)
        
        ##Temporary debug section
        print(f"Sections extracted: {len(chapter.sections)}")

        for section in chapter.sections:
            print(
                f"  L{section.level} "
                f"{section.number or '-':6} "
                f"{section.title}"
            )
        
        
        # Extract concepts
        
        chapter = self.concept_extractor.extract(chapter)
        print(f"Concepts extracted: {len(chapter.concepts)}")
               
        for concept in chapter.concepts:
            print(f" - {concept.title}")
            
            
            # Future Sprint 4
        # chapter = self.formula_extractor.extract(chapter)
        # chapter = self.example_extractor.extract(chapter)
        # chapter = self.exercise_extractor.extract(chapter)
        # chapter = self.figure_extractor.extract(chapter)

        print(f"Parsed Chapter : {chapter.metadata.order}")
        print(f"Title          : {chapter.metadata.title}")

        curriculum_id = self.writer.save(chapter)

        print("Firestore write completed.")

        return curriculum_id