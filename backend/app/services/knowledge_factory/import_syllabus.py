from pathlib import Path
import json

from app.services.knowledge_factory.syllabus_parser import SyllabusParser
from app.services.knowledge_factory.syllabus_firestore_writer import (
    SyllabusFirestoreWriter,
)
from app.services.knowledge_factory.syllabus_curriculum_linker import (
    SyllabusCurriculumLinker,
)


import sys
from pathlib import Path

def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("python import_syllabus.py <azure_result.json>")
        return

    json_path = Path(sys.argv[1])

    if not json_path.exists():
        raise FileNotFoundError(f"{json_path} not found.")
    print("=" * 80)
    print("MathVerse Syllabus Import")
    print("=" * 80)

    with open(json_path, "r", encoding="utf-8") as f:
        azure_json = json.load(f)

    parser = SyllabusParser()

    syllabus = parser.parse(azure_json, source_path=str(json_path))

    linker = SyllabusCurriculumLinker()

    syllabus = linker.link_syllabus(syllabus)

    writer = SyllabusFirestoreWriter()

    writer.save(syllabus)

    print()
    print("Import completed successfully.")
    print(f"Board     : {syllabus.board}")
    print(f"Grade     : {syllabus.grade}")
    print(f"Subject   : {syllabus.subject}")
    print(f"Chapters  : {len(syllabus.chapters)}")


if __name__ == "__main__":
    main()
