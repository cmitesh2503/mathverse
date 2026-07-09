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

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from app.core import config


class AzureLayoutService:
    """
    Converts one PDF into Azure Layout output.
    """

    def __init__(self) -> None:

        print("Endpoint:", config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT)
        print("Key Exists:", bool(config.AZURE_DOCUMENT_INTELLIGENCE_KEY))

        self.client = DocumentIntelligenceClient(
            endpoint=config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(
                config.AZURE_DOCUMENT_INTELLIGENCE_KEY
            ),
        )

    def analyze(
        self,
        pdf_file: str | Path,
    ) -> Path:

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

        #
        # Save Markdown
        #

        markdown_file.write_text(
            result.content,
            encoding="utf-8",
        )

        #
        # Save Raw JSON
        #

        json_file.write_text(
            json.dumps(
                result.as_dict(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return markdown_file