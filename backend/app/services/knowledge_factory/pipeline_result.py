from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DocumentPipelineResult:
    """
    Output of document processing pipelines.

    Chapter importers read merged markdown. Syllabus PDF importers read Azure
    Layout JSON when json_files are present.
    """

    markdown: str

    merged_markdown_file: Path

    chunk_files: list[Path]

    markdown_files: list[Path]

    json_files: list[Path]


ChapterPipelineResult = DocumentPipelineResult
