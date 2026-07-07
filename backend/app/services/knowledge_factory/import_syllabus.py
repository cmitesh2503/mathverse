from pathlib import Path
import json

from app.services.knowledge_factory.syllabus_parser import SyllabusParser
from app.services.knowledge_factory.firestore_writer import FirestoreWriter


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

    curriculum = parser.parse(azure_json)

    writer = FirestoreWriter()

    writer.save_curriculum(curriculum)

    print()
    print("Import completed successfully.")
    print(f"Exam      : {curriculum.exam}")
    print(f"Subject   : {curriculum.subject}")
    print(f"Chapters  : {len(curriculum.chapters)}")


if __name__ == "__main__":
    main()