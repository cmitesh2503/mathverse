import os
from PyPDF2 import PdfReader

PDF_DIR = "backend/app/data/pdfs/std_10"
OUTPUT_FILE = "backend/data/processed_content.txt"


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


def run_ingestion():
    all_text = ""

    for file in os.listdir(PDF_DIR):
        if file.endswith(".pdf"):
            path = os.path.join(PDF_DIR, file)
            print(f"Processing {file}...")

            text = extract_text_from_pdf(path)
            all_text += f"\n\n===== {file} =====\n\n"
            all_text += text

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(all_text)

    print("✅ Ingestion complete!")


if __name__ == "__main__":
    run_ingestion()