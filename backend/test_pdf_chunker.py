from pathlib import Path

from app.services.pdf_utils import PDFChunker

pdf = Path(r"C:\Users\mites\Downloads\Matrices.pdf")

chunker = PDFChunker()

chunks = chunker.split(pdf)

print()

print("=" * 80)
print("PDF Chunker")
print("=" * 80)

for chunk in chunks:
    print(chunk)

print()

print("Chunks :", len(chunks))