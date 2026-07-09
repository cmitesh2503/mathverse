from pathlib import Path

from app.services.knowledge_factory.chapter_pipeline import (
    ChapterPipeline,
)

pipeline = ChapterPipeline()

merged = pipeline.process(

    Path(
        r"C:\Users\mites\Downloads\Matrices.pdf"
    )

)

print()

print("=" * 80)

print(merged)

print("=" * 80)