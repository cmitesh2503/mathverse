import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.pipeline_result import DocumentPipelineResult
from app.services.knowledge_factory.syllabus_importer import SyllabusImporter
from app.services.knowledge_factory.syllabus_parser import SyllabusParser
from app.services.knowledge_factory.syllabus_pipeline import SyllabusPipeline


def test_syllabus_pipeline_extracts_open_document_without_pdf_chunks(tmp_path):
    odf_file = tmp_path / "jee-main.odf"
    content_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <office:document-content
        xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
        xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
      <office:body>
        <office:text>
          <text:h text:outline-level="1">Joint Entrance Examination (Main) 2026 Syllabus</text:h>
          <text:h text:outline-level="1">Mathematics</text:h>
          <text:p>Unit I: Sets, Relations and Functions</text:p>
          <text:p>Relations: reflexive, symmetric, transitive</text:p>
          <text:p>Unit II: Matrices and Determinants</text:p>
          <text:p>Matrices: algebra of matrices, inverse of a matrix</text:p>
          <text:h text:outline-level="1">Physics</text:h>
          <text:p>Unit I: Physics and Measurement</text:p>
          <text:p>Units: dimensions, errors</text:p>
          <text:h text:outline-level="1">Chemistry</text:h>
          <text:p>Unit I: Some Basic Concepts in Chemistry</text:p>
          <text:p>Mole concept: concentration, stoichiometry</text:p>
        </office:text>
      </office:body>
    </office:document-content>
    """

    with zipfile.ZipFile(odf_file, "w") as archive:
        archive.writestr("content.xml", content_xml)

    result = SyllabusPipeline().process(
        odf_file,
        output_root=tmp_path,
    )

    assert result.chunk_files == []
    assert result.json_files == []
    assert "# Mathematics" in result.markdown
    assert "# Physics" in result.markdown

    syllabus = SyllabusParser().parse_markdown(
        result.markdown,
        source_path="syllabus/jee/jee-main.odf",
    )

    assert syllabus.subject == "Mathematics"
    assert [chapter.title for chapter in syllabus.chapters] == [
        "Sets, Relations and Functions",
        "Matrices and Determinants",
    ]


def test_syllabus_pipeline_extracts_pdf_from_azure_json_without_pdf_chunks(tmp_path):
    pdf_file = tmp_path / "jee-main.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n% syllabus test\n")

    pipeline = SyllabusPipeline()
    azure_document = {
        "content": """
        # Joint Entrance Examination (Main) 2026 Syllabus

        # Mathematics
        Unit I: Sets, Relations and Functions
        Relations: reflexive, symmetric, transitive

        # Physics
        Unit I: Physics and Measurement
        Units: dimensions, errors
        """
    }

    class FakeLayout:
        def analyze(self, path, output_dir=None):
            assert path == pdf_file
            assert output_dir == tmp_path

            json_file = Path(output_dir) / "jee-main.json"
            markdown_file = Path(output_dir) / "jee-main.md"
            json_file.write_text(
                json.dumps(
                    azure_document,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            markdown_file.write_text(
                azure_document["content"],
                encoding="utf-8",
            )

            return {
                "markdown": azure_document["content"],
                "json": azure_document,
                "markdown_file": markdown_file,
                "json_file": json_file,
            }

    pipeline._layout = FakeLayout()

    result = pipeline.process(
        pdf_file,
        output_root=tmp_path,
    )

    assert result.chunk_files == []
    assert result.json_files == [tmp_path / "jee-main.json"]

    syllabus = SyllabusParser().parse(
        json.loads(
            result.json_files[0].read_text(
                encoding="utf-8",
            )
        ),
        source_path="syllabus/jee/jee-main.pdf",
    )

    assert syllabus.subject == "Mathematics"
    assert [chapter.title for chapter in syllabus.chapters] == [
        "Sets, Relations and Functions",
    ]


def test_syllabus_pipeline_sanitizes_pdf_surrogates_before_writing(tmp_path):
    pdf_file = tmp_path / "jee-main.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n% syllabus test\n")

    pipeline = SyllabusPipeline()

    class FakeLayout:
        def analyze(self, path, output_dir=None):
            return {
                "markdown": "",
                "json": {
                    "content": "# JEE Main Mathematics Syllabus 2026\n\nUnit I: Matrices \ud83d\n",
                },
                "markdown_file": Path(output_dir) / "jee-main.md",
                "json_file": Path(output_dir) / "jee-main.json",
            }

    pipeline._layout = FakeLayout()

    result = pipeline.process(
        pdf_file,
        output_root=tmp_path,
    )

    assert "\ud83d" not in result.markdown
    assert result.merged_markdown_file.read_text(encoding="utf-8") == result.markdown
    assert "\ud83d" not in result.json_files[0].read_text(encoding="utf-8")


def test_syllabus_importer_parses_pdf_from_azure_json(tmp_path):
    pdf_file = tmp_path / "jee-main.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n% syllabus test\n")
    markdown_file = tmp_path / "jee-main.md"
    markdown_file.write_text(
        "# Mathematics\n\nUnit I: Should Not Be Used\n",
        encoding="utf-8",
    )
    json_file = tmp_path / "jee-main.json"
    json_file.write_text(
        json.dumps(
            {
                "content": """
                # Joint Entrance Examination (Main) 2026 Syllabus

                # Mathematics
                Unit I: Sets, Relations and Functions
                Relations: reflexive, symmetric, transitive
                """
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakePipeline:
        def process(self, document_file, output_root=None):
            assert document_file == pdf_file
            return DocumentPipelineResult(
                markdown=markdown_file.read_text(
                    encoding="utf-8",
                ),
                merged_markdown_file=markdown_file,
                chunk_files=[],
                markdown_files=[markdown_file],
                json_files=[json_file],
            )

    class FakeWriter:
        def __init__(self):
            self.syllabus = None

        def save(self, syllabus):
            self.syllabus = syllabus
            return syllabus.syllabus_id

    class FakeLinker:
        def link_syllabus(self, syllabus):
            syllabus.chapters[0].topics[0].curriculum_chapter_id = "chapter-001"
            syllabus.chapters[0].topics[0].curriculum_section_ids = [
                "1-1-relations"
            ]
            syllabus.chapters[0].topics[0].curriculum_concept_ids = [
                "relations"
            ]
            return syllabus

    importer = SyllabusImporter.__new__(SyllabusImporter)
    importer.pipeline = FakePipeline()
    importer.parser = SyllabusParser()
    importer.linker = FakeLinker()
    importer.writer = FakeWriter()

    syllabus_id = importer.import_document(
        pdf_file,
        source_path="syllabus/jee/jee-main.pdf",
        output_root=tmp_path,
    )

    assert syllabus_id == "jee_jee-main_mathematics"
    assert [
        chapter.title
        for chapter in importer.writer.syllabus.chapters
    ] == ["Sets, Relations and Functions"]
    topic = importer.writer.syllabus.chapters[0].topics[0]
    assert topic.curriculum_chapter_id == "chapter-001"
    assert topic.curriculum_section_ids == ["1-1-relations"]
    assert topic.curriculum_concept_ids == ["relations"]
