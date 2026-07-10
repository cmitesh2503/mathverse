import logging
import sys
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

from compiler import KnowledgeCompiler

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)

compiler = KnowledgeCompiler()


SUPPORTED_FOLDERS = (

    "curriculum/",

    "ncert/",

    "reference/",

    "pyq/",

    "teacher_assets/",

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

    if not blob_name.lower().endswith(".pdf"):

        logger.info(
            "Ignoring non-PDF file."
        )

        return

    if not blob_name.startswith(
        SUPPORTED_FOLDERS
    ):

        logger.info(
            f"Ignoring unsupported folder: {blob_name}"
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

        result = compiler.compile(

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

    if blob_name.startswith(
        "curriculum/"
    ):
        return "curriculum"

    if blob_name.startswith(
        "ncert/"
    ):
        return "ncert"

    if blob_name.startswith(
        "reference/"
    ):
        return "reference"

    if blob_name.startswith(
        "pyq/"
    ):
        return "pyq"

    if blob_name.startswith(
        "teacher_assets/"
    ):
        return "teacher_assets"

    return "unknown"
