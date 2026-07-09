"""
MathVerse

Shared PDF Utilities

Reusable PDF operations shared across:

- Knowledge Factory
- RAG Ingestion
- Future OCR pipelines

Business logic MUST NOT exist here.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter


class PDFChunker:
    """
    Splits a PDF into smaller PDFs.

    Example

    -------
    chunker = PDFChunker()

    files = chunker.split(
        "Matrices.pdf",
        pages_per_chunk=2,
    )
    """

    def split(
        self,
        pdf_path: str | Path,
        pages_per_chunk: int = 2,
        output_root: str | Path = "temp",
    ) -> List[Path]:

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        reader = PdfReader(str(pdf_path))

        total_pages = len(reader.pages)

        output_dir = (
            Path(output_root)
            / pdf_path.stem.lower().replace(" ", "_")
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        chunk_files: List[Path] = []

        chunk_number = 1

        for start_page in range(
            0,
            total_pages,
            pages_per_chunk,
        ):

            writer = PdfWriter()

            end_page = min(
                start_page + pages_per_chunk,
                total_pages,
            )

            for page_index in range(
                start_page,
                end_page,
            ):
                writer.add_page(
                    reader.pages[page_index]
                )

            chunk_path = (
                output_dir
                / f"chunk_{chunk_number:03d}.pdf"
            )

            with chunk_path.open("wb") as fp:
                writer.write(fp)

            chunk_files.append(chunk_path)

            chunk_number += 1

        return chunk_files