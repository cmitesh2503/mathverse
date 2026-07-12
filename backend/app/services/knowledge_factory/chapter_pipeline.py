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

import tempfile
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
        output_root: str | Path | None = None,
    ) -> ChapterPipelineResult:

        pdf_file = Path(pdf_file)

        chunk_root = self._resolve_output_root(
            pdf_file,
            output_root,
        )

        chunks = self.chunker.split(
            pdf_file,
            pages_per_chunk=2,
            output_root=chunk_root,
        )

        markdown_files: list[Path] = []

        json_files: list[Path] = []

        print("=" * 80)
        print("Processing PDF Chunks")
        print("=" * 80)

        for chunk in chunks:

            print(f"Analyzing {chunk.name}")

            layout = self.layout.analyze(chunk)

            markdown_files.append(
                layout["markdown_file"]
            )

            json_files.append(
                layout["json_file"]
            )

        if not markdown_files:
            raise ValueError(
                f"No PDF chunks were produced for {pdf_file}"
            )

        merged = self._merge_markdown(
            markdown_files
        )

        print(f"Merged Markdown created: {merged.name}")

        return ChapterPipelineResult(
            markdown=merged.read_text(
                encoding="utf-8",
            ),
            merged_markdown_file=merged,
            chunk_files=chunks,
            markdown_files=markdown_files,
            json_files=json_files,
        )

    def _resolve_output_root(
        self,
        pdf_file: Path,
        output_root: str | Path | None,
    ) -> Path:

        if output_root is not None:
            return Path(output_root)

        base_dir = Path(tempfile.gettempdir()) / "mathverse"

        base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        prefix = (
            pdf_file.stem
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        return Path(
            tempfile.mkdtemp(
                prefix=f"{prefix}_",
                dir=base_dir,
            )
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

            for md in sorted(markdown_files):

                merged.write(md.read_text(encoding="utf-8"))

                merged.write("\n\n")

                merged.write("=" * 80)

                merged.write("\n\n")

        return output
