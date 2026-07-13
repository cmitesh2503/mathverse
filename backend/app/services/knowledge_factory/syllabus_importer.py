from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from app.services.knowledge_factory.syllabus_firestore_writer import (
    SyllabusFirestoreWriter,
)
from app.services.knowledge_factory.syllabus_curriculum_linker import (
    SyllabusCurriculumLinker,
)
from app.services.knowledge_factory.syllabus_parser import SyllabusParser
from app.services.knowledge_factory.syllabus_pipeline import SyllabusPipeline


class SyllabusImporter:
    """
    Orchestrates importing a syllabus PDF into Firestore.

    Responsibilities
    ----------------
    1. Run the syllabus document pipeline
    2. Parse Azure Layout JSON for PDFs, or markdown for OpenDocument files
    3. Persist the syllabus hierarchy
    """

    def __init__(self) -> None:
        self.pipeline = SyllabusPipeline()
        self.parser = SyllabusParser()
        self.linker = SyllabusCurriculumLinker()
        self.writer = SyllabusFirestoreWriter()

    def import_document(
        self,
        document_file: str | Path,
        *,
        source_path: str = "",
        output_root: str | Path | None = None,
    ) -> str:
        print("=" * 80)
        print("MathVerse Syllabus Import")
        print("=" * 80)

        source_metadata = self._metadata_from_source_path(
            source_path
        )

        pipeline = self.pipeline.process(
            document_file,
            output_root=output_root,
        )

        parse_kwargs = {
            "source_path": source_path,
            "board": source_metadata.get("board"),
            "grade": source_metadata.get("grade"),
        }

        if pipeline.json_files:
            syllabus = self.parser.parse(
                self._load_azure_json(
                    pipeline.json_files,
                ),
                **parse_kwargs,
            )
        else:
            syllabus = self.parser.parse_markdown(
                pipeline.markdown,
                **parse_kwargs,
            )

        print(
            f"Syllabus parsed: {syllabus.board} {syllabus.grade} "
            f"with {len(syllabus.chapters)} chapters"
        )

        syllabus = self.linker.link_syllabus(syllabus)

        syllabus_id = self.writer.save(syllabus)

        print("Syllabus Firestore write completed.")

        return syllabus_id

    def import_pdf(
        self,
        pdf_file: str | Path,
        *,
        source_path: str = "",
        output_root: str | Path | None = None,
    ) -> str:
        return self.import_document(
            pdf_file,
            source_path=source_path,
            output_root=output_root,
        )

    def _metadata_from_source_path(
        self,
        source_path: str,
    ) -> dict[str, str]:
        if not source_path:
            return {}

        normalized = source_path.replace("\\", "/").strip("/")
        parts = [part for part in PurePosixPath(normalized).parts if part]

        if not parts:
            return {}

        if parts[0].lower() != "syllabus":
            raise ValueError(
                f"SyllabusImporter expected a syllabus/ object path, got: {source_path}"
            )

        metadata: dict[str, str] = {}

        board = ""
        if len(parts) >= 2:
            board = self._board_from_path_part(parts[1])
            if board:
                metadata["board"] = board

        grade_parts = parts[2:] if len(parts) >= 3 and board else parts[1:]

        grade = self._identify_grade(
            grade_parts
        )
        if grade:
            metadata["grade"] = grade
        elif metadata.get("board") == "jee":
            metadata["grade"] = "jee-main"

        return metadata

    def _load_azure_json(
        self,
        json_files: list[Path],
    ) -> dict[str, Any]:
        documents = [
            json.loads(
                Path(json_file).read_text(
                    encoding="utf-8",
                )
            )
            for json_file in json_files
        ]

        if len(documents) == 1:
            return documents[0]

        return {
            "content": "\n\n".join(
                self.parser.content_from_document(document)
                for document in documents
            ),
            "documents": documents,
        }

    def _identify_grade(
        self,
        parts: list[str],
    ) -> str:
        for part in parts:
            slug = self._slug(part.replace(".pdf", ""))

            if slug in {"jee", "jee-main", "main"}:
                return "jee-main"

            if slug in {"jee-advanced", "advanced"}:
                return "jee-advanced"

            match = re.search(r"(?:grade|class)-?(\d{1,2})", slug)
            if match:
                return f"grade-{int(match.group(1)):02d}"

        return ""

    def _board_from_path_part(
        self,
        value: str,
    ) -> str:
        slug = self._slug(PurePosixPath(value).stem)

        if slug in {"cbse", "central-board-of-secondary-education"}:
            return "cbse"

        if slug in {"jee", "jee-main", "jee-advanced"}:
            return "jee"

        return ""

    def _slug(
        self,
        value: str,
    ) -> str:
        slug = str(value or "").lower()
        slug = slug.replace("&", "and")
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")
