"""
Shared document pipeline for Knowledge Factory ingestion.

Owns only PDF chunking, Azure Layout processing, and markdown merge.
Parsing and Firestore writes stay in the concrete importers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.knowledge_factory.pipeline_result import (
    DocumentPipelineResult,
)


class BaseDocumentPipeline:
    """
    Reusable PDF -> Azure Layout -> merged markdown pipeline.
    """

    def __init__(self, pages_per_chunk: int = 2) -> None:
        self.pages_per_chunk = pages_per_chunk
        self._chunker = None
        self._layout = None

    @property
    def chunker(self):
        if self._chunker is None:
            from app.services.pdf_utils import PDFChunker

            self._chunker = PDFChunker()

        return self._chunker

    @property
    def layout(self):
        if self._layout is None:
            from app.services.knowledge_factory.azure_layout_service import (
                AzureLayoutService,
            )

            self._layout = AzureLayoutService()

        return self._layout

    def process(
        self,
        pdf_file: str | Path,
        output_root: str | Path | None = None,
    ) -> DocumentPipelineResult:
        pdf_file = Path(pdf_file)
        chunk_root = self._resolve_output_root(
            pdf_file,
            output_root,
        )

        chunks = self.split_pdf(
            pdf_file,
            chunk_root,
        )

        markdown_files, json_files = self.process_layout(
            chunks
        )

        if not markdown_files:
            raise ValueError(
                f"No PDF chunks were produced for {pdf_file}"
            )

        merged = self.merge_markdown(
            markdown_files
        )

        print(f"Merged Markdown created: {merged.name}")

        return DocumentPipelineResult(
            markdown=merged.read_text(
                encoding="utf-8",
            ),
            merged_markdown_file=merged,
            chunk_files=chunks,
            markdown_files=markdown_files,
            json_files=json_files,
        )

    def split_pdf(
        self,
        pdf_file: Path,
        output_root: Path,
    ) -> list[Path]:
        return self.chunker.split(
            pdf_file,
            pages_per_chunk=self.pages_per_chunk,
            output_root=output_root,
        )

    def process_layout(
        self,
        chunks: list[Path],
    ) -> tuple[list[Path], list[Path]]:
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

        return markdown_files, json_files

    def merge_markdown(
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

    # Compatibility aliases for existing private helper naming.
    def _create_chunks(
        self,
        pdf_file: Path,
        output_root: Path,
    ) -> list[Path]:
        return self.split_pdf(
            pdf_file,
            output_root,
        )

    def _process_chunks(
        self,
        chunks: list[Path],
    ) -> tuple[list[Path], list[Path]]:
        return self.process_layout(chunks)

    def _merge_markdown(
        self,
        markdown_files: list[Path],
    ) -> Path:
        return self.merge_markdown(markdown_files)
