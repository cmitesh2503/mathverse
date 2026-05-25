import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
CBSE_DIR = BACKEND_DIR / "data" / "curriculum" / "cbse"
SOURCE_PDF_DIR = BACKEND_DIR / "app" / "data" / "pdfs"

# Define the phase-aware directory structure dynamically
structure = {}
for grade in range(9, 13):  # Generates for grades 9, 10, 11, and 12
    grade_key = f"grade_{grade}"
    structure[grade_key] = {}
    for ch in range(1, 16):  # Generates chapters 1 through 15
        ch_key = f"ch_{ch:02d}"  # Formats as ch_01, ch_02, etc.
        structure[grade_key][ch_key] = ["theory.pdf", "practice.pdf", "solution.pdf"]

def get_sample_pdf():
    """Try to find an existing valid PDF from the old directory."""
    if SOURCE_PDF_DIR.exists():
        pdfs = list(SOURCE_PDF_DIR.rglob("*.pdf"))
        if pdfs:
            return pdfs[0]
    return None

def main():
    print(f"Creating curriculum structure at: {CBSE_DIR}")
    sample_pdf = get_sample_pdf()
    
    if sample_pdf:
        print(f"Found existing PDF! Using '{sample_pdf.name}' to generate valid dummy files.")
    else:
        print("No existing PDFs found. Will create empty .pdf files (PyPDFLoader may skip these).")

    for grade, chapters in structure.items():
        for chapter, files in chapters.items():
            chapter_dir = CBSE_DIR / grade / chapter
            chapter_dir.mkdir(parents=True, exist_ok=True)
            
            for pdf_file in files:
                target_path = chapter_dir / pdf_file
                if not target_path.exists():
                    if sample_pdf:
                        shutil.copy2(sample_pdf, target_path)
                    else:
                        target_path.touch()

    print("\n✅ Setup complete! The folder structure is ready.")

if __name__ == "__main__":
    main()