import sys

from app.services.knowledge_factory.chapter_importer import ChapterImporter


def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("python import_chapter.py <azure_json>")
        return

    importer = ChapterImporter()

    curriculum_id = importer.import_json(sys.argv[1])

    print()
    print("=" * 80)
    print("Import Successful")
    print("=" * 80)
    print(curriculum_id)


if __name__ == "__main__":
    main()