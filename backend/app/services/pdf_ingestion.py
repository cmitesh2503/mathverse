from pathlib import Path

from PyPDF2 import PdfReader

APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
PDF_DIR = APP_DIR / "data" / "pdfs" / "std_10"
OUTPUT_FILE = BACKEND_DIR / "data" / "processed_content.txt"


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


def run_ingestion():
    all_text = ""

    for path in PDF_DIR.glob("*.pdf"):
        print(f"Processing {path.name}...")

        text = extract_text_from_pdf(path)
        all_text += f"\n\n===== {path.name} =====\n\n"
        all_text += text

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write(all_text)

    print("✅ Ingestion complete!")


if __name__ == "__main__":
    run_ingestion()
