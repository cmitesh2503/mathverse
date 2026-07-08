from pathlib import Path

from app.services.knowledge_factory.chapter_parser import ChapterParser
from app.services.knowledge_factory.section_parser import SectionParser

chapter = ChapterParser().parse(
    Path(r"C:\Users\mites\Downloads\Matrices.json")
)

chapter = SectionParser().parse(chapter)

for section in chapter.sections:
    preview = section.content.splitlines()[0] if section.content else ""
    print(
        f"L{section.level} | {section.number:6} | {section.title}"
    )
    print(f"    {preview}")
    print("-" * 80)