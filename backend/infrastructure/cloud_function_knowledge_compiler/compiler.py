from datetime import datetime
import logging
import shutil
import tempfile
from pathlib import Path

from google.cloud import storage

from app.services.knowledge_factory.chapter_importer import (
    ChapterImporter,
)
from app.services.knowledge_factory.syllabus_importer import (
    SyllabusImporter,
)

logger = logging.getLogger(__name__)


class KnowledgeCompiler:

    def __init__(self):

        self.storage = storage.Client()

        self.chapter_importer = ChapterImporter()

        self.syllabus_importer = SyllabusImporter()

        # Backward-compatible alias for any direct callers that still access
        # KnowledgeCompiler.importer.
        self.importer = self.chapter_importer

    def compile(
        self,
        bucket_name: str,
        blob_name: str,
        document_type: str = "curriculum",
    ):

        logger.info(
            "Knowledge compilation started."
        )

        started = datetime.utcnow()

        logger.info(
            "Downloading PDF"
        )

        pdf_file = self._download_pdf(
            bucket_name,
            blob_name,
        )

        try:

            import_result = self._import_document(
                pdf_file,
                blob_name,
                document_type,
            )

        finally:

            shutil.rmtree(
                pdf_file.parent,
                ignore_errors=True,
            )

        finished = datetime.utcnow()

        return {

            "success": True,

            "bucket": bucket_name,

            "file": blob_name,

            "document_type": document_type,

            "started": started.isoformat(),

            "completed": finished.isoformat(),

            **import_result,

        }

    def _import_document(
        self,
        pdf_file: Path,
        blob_name: str,
        document_type: str,
    ) -> dict:

        normalized_type = (document_type or "").lower()

        if normalized_type == "syllabus":

            syllabus_id = self.syllabus_importer.import_document(
                pdf_file,
                source_path=blob_name,
                output_root=pdf_file.parent,
            )

            return {
                "syllabus_id": syllabus_id,
            }

        if normalized_type in {"curriculum", "jee_raw_pdf"}:

            curriculum_id = self.chapter_importer.import_pdf(
                pdf_file,
                output_root=pdf_file.parent,
            )

            return {
                "curriculum_id": curriculum_id,
            }

        raise ValueError(
            f"Unsupported document_type={document_type!r} for {blob_name}"
        )

    def _download_pdf(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Path:

        bucket = self.storage.bucket(bucket_name)

        blob = bucket.blob(object_name)

        temp_root = Path(tempfile.gettempdir()) / "mathverse"

        temp_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_dir = Path(
            tempfile.mkdtemp(
                prefix="knowledge_",
                dir=temp_root,
            )
        )

        local_pdf = temp_dir / Path(object_name).name

        blob.download_to_filename(
            str(local_pdf)
        )

        return local_pdf
