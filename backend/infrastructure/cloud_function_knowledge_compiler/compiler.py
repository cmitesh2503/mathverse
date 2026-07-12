from datetime import datetime
import logging
import shutil
import tempfile
from pathlib import Path

from google.cloud import storage

from app.services.knowledge_factory.chapter_importer import (
    ChapterImporter,
)

logger = logging.getLogger(__name__)


class KnowledgeCompiler:

    def __init__(self):

        self.storage = storage.Client()

        self.importer = ChapterImporter()

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

            curriculum_id = self.importer.import_pdf(
                pdf_file,
                output_root=pdf_file.parent,
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

            "curriculum_id": curriculum_id,

            "started": started.isoformat(),

            "completed": finished.isoformat(),

        }

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
