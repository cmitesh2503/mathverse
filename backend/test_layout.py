import os
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

ENDPOINT = os.getenv(
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
    "https://mathverse-docai.cognitiveservices.azure.com/",
)
KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
if not KEY:
    raise RuntimeError("Set AZURE_DOCUMENT_INTELLIGENCE_KEY before running this script.")

PDF = Path(os.getenv("MATHVERSE_LAYOUT_TEST_PDF", r"C:\Users\mites\Downloads\Matrices.pdf"))

client = DocumentIntelligenceClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(KEY),
)

with open(PDF, "rb") as f:
    document = AnalyzeDocumentRequest(bytes_source=f.read())

    poller = client.begin_analyze_document(
        "prebuilt-layout",
        #AnalyzeDocumentRequest(
        #    url_source="https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"
       # ),
        body=document,
        output_content_format="markdown",
    )

result = poller.result()

result = poller.result()

print("=" * 80)
print("Analysis Summary")
print("=" * 80)

print("Pages:", len(result.pages))
print("Model ID:", result.model_id)
print("API Version:", getattr(result, "api_version", "N/A"))
print("Warnings:", getattr(result, "warnings", None))
print("Languages:", getattr(result, "languages", None))

print()
print("=" * 80)
print("Markdown Preview")
print("=" * 80)

print(result.content[:3000])
