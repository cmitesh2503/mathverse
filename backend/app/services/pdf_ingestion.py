from pathlib import Path

from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract

APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
PDF_ROOT_DIR = APP_DIR / "data" / "pdfs"
OUTPUT_FILE = BACKEND_DIR / "data" / "processed_content.txt"
MIN_EXTRACTED_TEXT_LEN = 50


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    page_texts = []

    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if len(page_text) < MIN_EXTRACTED_TEXT_LEN:
            ocr_images = convert_from_path(str(file_path), first_page=len(page_texts) + 1, last_page=len(page_texts) + 1)
            ocr_text = ""
            for image in ocr_images:
                ocr_text += pytesseract.image_to_string(image)
            page_text = ocr_text.strip() or page_text
        page_texts.append(page_text)

    return "\n".join(page_texts)


def run_ingestion():
    all_text = ""

    for path in PDF_ROOT_DIR.rglob("*.pdf"):
        print(f"Processing {path.relative_to(PDF_ROOT_DIR)}...")

        text = extract_text_from_pdf(path)
        all_text += f"\n\n===== {path.name} =====\n\n"
        all_text += text

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write(all_text)

    print("✅ Ingestion complete!")


if __name__ == "__main__":
    run_ingestion()
