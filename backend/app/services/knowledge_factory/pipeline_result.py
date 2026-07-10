from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChapterPipelineResult:
    """
    Output of the document ingestion pipeline.

    One Azure call.

    Multiple downstream consumers.
    """

    markdown: str

    azure_json: dict