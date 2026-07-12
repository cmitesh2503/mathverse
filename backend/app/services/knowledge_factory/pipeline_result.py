from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ChapterPipelineResult:
    """
    Output of the PDF-to-markdown pipeline.

    JSON remains per chunk. Downstream parsers read only merged markdown.
    """

    markdown: str

    merged_markdown_file: Path

    chunk_files: list[Path]

    markdown_files: list[Path]

    json_files: list[Path]
