"""
MathVerse Knowledge Factory syllabus pipeline.

PDF syllabuses use Azure Document Intelligence JSON.
OpenDocument syllabuses are converted directly to markdown without chunking.
"""

from __future__ import annotations

import html
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from app.services.knowledge_factory.base_document_pipeline import (
    BaseDocumentPipeline,
)
from app.services.knowledge_factory.pipeline_result import (
    DocumentPipelineResult,
)
from app.services.knowledge_factory.text_sanitizer import (
    sanitize_json_value,
    sanitize_text,
)


class SyllabusPipeline(BaseDocumentPipeline):
    """
    Syllabus document to Azure JSON or markdown.
    """

    _OPEN_DOCUMENT_EXTENSIONS = {".odf", ".odt"}

    def __init__(self) -> None:
        super().__init__()

    def process(
        self,
        syllabus_file: str | Path,
        output_root: str | Path | None = None,
    ) -> DocumentPipelineResult:
        syllabus_file = Path(syllabus_file)
        suffix = syllabus_file.suffix.lower()

        if suffix in self._OPEN_DOCUMENT_EXTENSIONS:
            return self._process_open_document(
                syllabus_file,
                output_root,
            )

        if suffix == ".pdf":
            return self._process_pdf(
                syllabus_file,
                output_root,
            )

        raise ValueError(
            f"Unsupported syllabus file type: {syllabus_file.suffix}"
        )

    def _process_pdf(
        self,
        syllabus_file: Path,
        output_root: str | Path | None,
    ) -> DocumentPipelineResult:
        output_dir = self._resolve_output_root(
            syllabus_file,
            output_root,
        )
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        layout = self.layout.analyze(
            syllabus_file,
            output_dir=output_dir,
        )

        azure_json = sanitize_json_value(
            layout["json"]
        )
        markdown = self._content_from_azure_json(
            azure_json
        )
        if not markdown:
            markdown = layout.get("markdown") or ""
        markdown = self._sanitize_markdown(markdown)

        if not markdown.strip():
            raise ValueError(
                f"No Azure Layout content found in syllabus PDF: {syllabus_file}"
            )

        markdown_file = Path(
            layout["markdown_file"]
        )
        markdown_file.write_text(
            markdown,
            encoding="utf-8",
        )

        json_file = Path(
            layout["json_file"]
        )
        if not json_file.exists():
            json_file.write_text(
                json.dumps(
                    azure_json,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        return DocumentPipelineResult(
            markdown=markdown,
            merged_markdown_file=markdown_file,
            chunk_files=[],
            markdown_files=[markdown_file],
            json_files=[json_file],
        )

    def _process_open_document(
        self,
        syllabus_file: Path,
        output_root: str | Path | None,
    ) -> DocumentPipelineResult:
        output_dir = self._resolve_output_root(
            syllabus_file,
            output_root,
        )
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        markdown = self._open_document_to_markdown(
            syllabus_file
        )
        markdown = self._sanitize_markdown(markdown)

        markdown_file = output_dir / f"{syllabus_file.stem}.md"
        markdown_file.write_text(
            markdown,
            encoding="utf-8",
        )

        return DocumentPipelineResult(
            markdown=markdown,
            merged_markdown_file=markdown_file,
            chunk_files=[],
            markdown_files=[markdown_file],
            json_files=[],
        )

    def _resolve_output_root(
        self,
        syllabus_file: Path,
        output_root: str | Path | None,
    ) -> Path:
        if output_root is not None:
            return Path(output_root)

        base_dir = Path(tempfile.gettempdir()) / "mathverse"
        base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return Path(
            tempfile.mkdtemp(
                prefix=f"{syllabus_file.stem.lower()}_",
                dir=base_dir,
            )
        )

    def _open_document_to_markdown(
        self,
        syllabus_file: Path,
    ) -> str:
        with zipfile.ZipFile(syllabus_file) as archive:
            try:
                content_xml = archive.read("content.xml")
            except KeyError as exc:
                raise ValueError(
                    f"{syllabus_file} is not a valid OpenDocument file."
                ) from exc

        root = ElementTree.fromstring(content_xml)
        lines = self._extract_markdown_lines(root)
        markdown = "\n".join(lines)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        return markdown.strip() + "\n"

    def _content_from_azure_json(
        self,
        document: dict[str, Any],
    ) -> str:
        content = document.get("content")
        if isinstance(content, str):
            return content

        analyze_result = document.get("analyzeResult")
        if isinstance(analyze_result, dict):
            content = analyze_result.get("content")
            if isinstance(content, str):
                return content

        return ""

    def _sanitize_markdown(
        self,
        markdown: str,
    ) -> str:
        markdown = sanitize_text(markdown)
        markdown = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", markdown)
        markdown = re.sub(r"[ \t]+", " ", markdown)
        return markdown

    def _extract_markdown_lines(
        self,
        root: ElementTree.Element,
    ) -> list[str]:
        lines: list[str] = []

        for element in root.iter():
            local_name = self._local_name(element.tag)

            if local_name == "h":
                text = self._element_text(element)
                if text:
                    level = self._heading_level(element)
                    lines.append(
                        f"{'#' * level} {text}"
                    )
                    lines.append("")

            elif local_name == "p":
                text = self._element_text(element)
                if text:
                    lines.append(text)
                    lines.append("")

            elif local_name == "table-row":
                cells = [
                    self._element_text(child)
                    for child in list(element)
                    if self._local_name(child.tag) == "table-cell"
                ]
                cells = [cell for cell in cells if cell]
                if cells:
                    lines.append(
                        " | ".join(cells)
                    )
                    lines.append("")

        return lines

    def _heading_level(
        self,
        element: ElementTree.Element,
    ) -> int:
        for name, value in element.attrib.items():
            if self._local_name(name) == "outline-level" and value.isdigit():
                return max(
                    1,
                    min(int(value), 6),
                )
        return 2

    def _element_text(
        self,
        element: ElementTree.Element,
    ) -> str:
        text = "".join(element.itertext())
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _local_name(
        self,
        tag: str,
    ) -> str:
        return tag.rsplit("}", 1)[-1]
