"""
MathVerse Knowledge Factory

Azure Layout Service

Converts a PDF into Azure Document Intelligence
Layout output.

Responsibilities
----------------
- Call Azure Layout API
- Save raw JSON
- Save Markdown

No parsing.
No Firestore.
No knowledge extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from app.core import config
from app.services.knowledge_factory.text_sanitizer import (
    sanitize_json_value,
    sanitize_text,
)


class AzureLayoutService:
    """
    Converts one PDF into Azure Layout output.
    """

    def __init__(self) -> None:

        self.client = DocumentIntelligenceClient(
            endpoint=config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(
                config.AZURE_DOCUMENT_INTELLIGENCE_KEY
            ),
        )

    def analyze(
        self,
        pdf_file: str | Path,
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:

        pdf_file = Path(pdf_file)

        output_dir = (
            Path(output_dir)
            if output_dir is not None
            else pdf_file.parent
        )
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_file = output_dir / f"{pdf_file.stem}.json"

        markdown_file = output_dir / f"{pdf_file.stem}.md"

        with pdf_file.open("rb") as fp:

            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=fp,
                output_content_format="markdown",
            )

        result = poller.result()

        raw_json = sanitize_json_value(
            result.as_dict()
        )

        markdown = raw_json.get("content")
        if not isinstance(markdown, str):
            markdown = sanitize_text(
                result.content or ""
            )

        #
        # Save Markdown
        #

        markdown_file.write_text(
            markdown,
            encoding="utf-8",
        )

        #
        # Save Raw JSON
        #

        json_file.write_text(
            json.dumps(
                raw_json,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "markdown": markdown,
            "json": raw_json,
            "markdown_file": markdown_file,
            "json_file": json_file,
        }
