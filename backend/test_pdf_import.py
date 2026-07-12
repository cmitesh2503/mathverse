from pathlib import Path

from app.services.knowledge_factory.chapter_importer import (
    ChapterImporter,
)

pdf = Path(
    r"C:\Users\mites\Downloads\Matrices.pdf"
)

curriculum = ChapterImporter().import_pdf(
    pdf
)

print()
print("=" * 80)
print(curriculum)
print("=" * 80)