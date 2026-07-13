"""
MathVerse Knowledge Factory chapter pipeline.

Shared PDF chunking, Azure Layout processing, and markdown merge live in
BaseDocumentPipeline. Chapter-specific parsing happens in ChapterImporter.
"""

from __future__ import annotations

from app.services.knowledge_factory.base_document_pipeline import (
    BaseDocumentPipeline,
)


class ChapterPipeline(BaseDocumentPipeline):
    """
    Chapter PDF to merged Azure Layout markdown.
    """

    pass
