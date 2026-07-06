from datetime import datetime
import logging

from pipeline import (
    KnowledgePipeline
)

from document_loader import (
    DocumentLoader
)

from ocr_service import (
    OCRService
)

logger = logging.getLogger(__name__)


class KnowledgeCompiler:

    def __init__(self):

        self.loader = DocumentLoader()

        self.ocr = OCRService()

        self.pipeline = KnowledgePipeline()

    def compile(

        self,

        bucket_name: str,

        blob_name: str,

        document_type: str = "curriculum"

    ):

        logger.info(
            "Knowledge compilation started."
        )

        started = datetime.utcnow()

        pdf = self.loader.load_pdf(

            bucket_name,

            blob_name

        )

        text = self.ocr.extract_text(
            pdf
        )

        logger.info(
            "OCR extraction completed. Text length=%d",
            len(text) if isinstance(text, str) else 0,
        )

        if not isinstance(text, str) or not text.strip():
            raise ValueError("OCR extracted empty text from PDF.")

        graph = self.pipeline.build_knowledge(
            text
        )

        finished = datetime.utcnow()

        return {

            "success": True,

            "bucket": bucket_name,

            "file": blob_name,

            "document_type": document_type,

            "started": started.isoformat(),

            "completed": finished.isoformat(),

            "knowledge_graph": {

                "nodes_created": graph.nodes_created,

                "relationships_created": graph.relationships_created

            }

        }