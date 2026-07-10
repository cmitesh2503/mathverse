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

from app.services.knowledge_factory.pipeline_result import (
    ChapterPipelineResult,
)

class ChapterPipeline:

    def __init__(self) -> None:

        self.chunker = PDFChunker()

        self.layout = AzureLayoutService()

    def process(
        self,
        pdf_file: str | Path,
    ) -> ChapterPipelineResult:

        pdf_file = Path(pdf_file)

        chunks = self.chunker.split(
            pdf_file,
            pages_per_chunk=2,
            output_root=pdf_file.parent,
        )

        markdown_files = []
        azure_pages = []

        print("=" * 80)
        print("Processing PDF Chunks")
        print("=" * 80)

        for chunk in chunks:

            print(f"Analyzing {chunk.name}")

            layout = self.layout.analyze(chunk)

            markdown_file = (
                chunk.with_suffix(".md")
            )

            markdown_file.write_text(
                layout["markdown"],
                encoding="utf-8",
            )

            markdown_files.append(
                markdown_file
            )

            azure_pages.extend(
                layout["json"].get(
                    "pages",
                    []
                )
            )

        if not markdown_files:
            raise ValueError(
                f"No PDF chunks were produced for {pdf_file}"
            )

        merged = self._merge_markdown(
            markdown_files
        )

        return ChapterPipelineResult(
            markdown=merged.read_text(
                encoding="utf-8",
            ),
            azure_json={
                "pages": azure_pages,
            },
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
