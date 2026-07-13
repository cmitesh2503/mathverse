import logging
import sys
from functools import lru_cache
from pathlib import Path


FUNCTION_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = FUNCTION_DIR.parents[1]

for import_path in (
    SOURCE_ROOT,
    FUNCTION_DIR,
):
    import_path_value = str(import_path)

    if import_path_value not in sys.path:
        sys.path.insert(
            0,
            import_path_value,
        )

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_compiler():
    from compiler import KnowledgeCompiler

    return KnowledgeCompiler()


SUPPORTED_FOLDERS = (

    "curriculum/",

    "syllabus/",

    "raw-pdfs/",

)


def process_knowledge_document(event, context):
    """
    Cloud Storage Trigger

    Upload PDF

        ↓

    Knowledge Factory

        ↓

    Firestore
    """

    bucket_name = event.get("bucket")

    blob_name = event.get("name")

    if not bucket_name or not blob_name:

        logger.warning(
            "Invalid storage event."
        )

        return

    if not is_supported_document(
        blob_name
    ):

        logger.info(
            "Ignoring unsupported document type."
        )

        return

    if not blob_name.startswith(
        SUPPORTED_FOLDERS
    ):

        logger.info(
            f"Ignoring unsupported folder: {blob_name}"
        )

        return

    if is_misplaced_syllabus(
        blob_name
    ):

        logger.warning(
            "Ignoring syllabus PDF uploaded under curriculum/. "
            "Upload syllabus PDFs under syllabus/."
        )

        return

    logger.info("=" * 80)

    logger.info(
        "Knowledge Factory Triggered"
    )

    logger.info("=" * 80)

    document_type = get_document_type(
        blob_name
    )

    logger.info(
        f"Bucket : {bucket_name}"
    )

    logger.info(
        f"Blob   : {blob_name}"
    )

    logger.info(
        f"Document type : {document_type}"
    )

    try:

        result = get_compiler().compile(

            bucket_name=bucket_name,

            blob_name=blob_name,

            document_type=document_type

        )

        logger.info(
            "Knowledge compilation completed."
        )

        logger.info(result)

    except Exception:

        logger.exception(
            "Knowledge compilation failed."
        )

        raise


def get_document_type(
    blob_name: str
) -> str:

    if blob_name.startswith("curriculum/"):
        return "curriculum"

    if blob_name.startswith("syllabus/"):
        return "syllabus"

    if blob_name.startswith(
        "raw-pdfs/"
    ):
        return "jee_raw_pdf"

    return "unknown"


def is_misplaced_syllabus(
    blob_name: str
) -> bool:

    return (
        blob_name.startswith("curriculum/")
        and Path(blob_name).name.lower().startswith("syllabus")
    )


def is_supported_document(
    blob_name: str
) -> bool:

    suffix = Path(blob_name).suffix.lower()

    if blob_name.startswith("syllabus/"):
        return suffix in {
            ".pdf",
            ".odf",
            ".odt",
        }

    return suffix == ".pdf"
