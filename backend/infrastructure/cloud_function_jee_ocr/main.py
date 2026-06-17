import json
import os
from datetime import datetime

from google.cloud import storage
from google.cloud import firestore
from google.cloud import documentai

PROJECT_ID = os.environ["PROJECT_ID"]
PROCESSOR_ID = os.environ["PROCESSOR_ID"]
PROCESSOR_LOCATION = os.environ["PROCESSOR_LOCATION"]

storage_client = storage.Client()
firestore_client = firestore.Client(project=PROJECT_ID)


def process_pdf(event, context):
    """
    Trigger:
    gs://<project>-jee-assets/raw-pdfs/*.pdf
    """

    bucket_name = event["bucket"]
    
    file_name = event["name"]
    
    if not file_name.startswith("raw-pdfs/"):
        return

    if not file_name.lower().endswith(".pdf"):
        return

    print(f"Processing PDF: {file_name}")

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    pdf_bytes = blob.download_as_bytes()

    client = documentai.DocumentProcessorServiceClient()

    processor_name = client.processor_path(
        PROJECT_ID,
        PROCESSOR_LOCATION,
        PROCESSOR_ID
    )

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf"
        )
    )

    
    try:
        result = client.process_document(request=request)

    except Exception as e:

        firestore_client.collection(
            "jee_extraction_logs"
        ).add({
            "file_name": file_name,
            "error": str(e),
            "created_at": datetime.utcnow()
        })

        raise

    document = result.document

    ocr_json = {
        "file_name": file_name,
        "text": document.text,
        "pages": len(document.pages)
    }

    output_name = (
        file_name
        .replace("raw-pdfs/", "ocr-output/")
        .replace(".pdf", ".json")
    )

    output_blob = bucket.blob(output_name)

    output_blob.upload_from_string(
        json.dumps(ocr_json, ensure_ascii=False),
        content_type="application/json"
    )

    job_id = file_name.replace("/", "_")

    firestore_client.collection(
    "jee_import_jobs"
    ).document(job_id).set({
    "file_name": file_name,
    "status": "OCR_COMPLETED",
    "pages": len(document.pages),
    "created_at": datetime.utcnow()
     })

    print(f"OCR saved: {output_name}")