"""
MathVerse Knowledge Factory

Chapter Pipeline

Pipeline

PDF
 ↓
PDFChunker
 ↓
Azure Layout
 ↓
Markdown Merge
 ↓
merged.md

No parsing.
No Firestore.
"""

from __future__ import annotations

from pathlib import Path

from app.services.pdf_utils import PDFChunker
from app.services.knowledge_factory.azure_layout_service import (
    AzureLayoutService,
)


class ChapterPipeline:

    def __init__(self) -> None:

        self.chunker = PDFChunker()

        self.layout = AzureLayoutService()

    def process(
        self,
        pdf_file: str | Path,
    ) -> Path:

        pdf_file = Path(pdf_file)

        chunks = self.chunker.split(
            pdf_file,
            pages_per_chunk=2,
        )

        markdown_files = []

        print("=" * 80)
        print("Processing PDF Chunks")
        print("=" * 80)

        for chunk in chunks:

            print(f"Analyzing {chunk.name}")

            markdown = self.layout.analyze(chunk)

            markdown_files.append(markdown)

        merged = self._merge_markdown(markdown_files)

        print()

        print(f"Merged markdown : {merged}")

        return merged.read_text(
            encoding="utf-8",
        )

    def _merge_markdown(
        self,
        markdown_files: list[Path],
    ) -> Path:

        output = markdown_files[0].parent / "merged.md"

        with output.open(
            "w",
            encoding="utf-8",
        ) as merged:

            for md in markdown_files:

                merged.write(md.read_text(encoding="utf-8"))

                merged.write("\n\n")

                merged.write("=" * 80)

                merged.write("\n\n")

        return output