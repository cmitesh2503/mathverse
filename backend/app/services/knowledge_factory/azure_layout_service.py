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
    ) -> dict[str, Any]:

        pdf_file = Path(pdf_file)

        output_dir = pdf_file.parent

        json_file = output_dir / f"{pdf_file.stem}.json"

        markdown_file = output_dir / f"{pdf_file.stem}.md"

        with pdf_file.open("rb") as fp:

            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=fp,
                output_content_format="markdown",
            )

        result = poller.result()

        markdown = result.content or ""

        raw_json = result.as_dict()

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
