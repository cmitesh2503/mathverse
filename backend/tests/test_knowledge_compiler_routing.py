import sys
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "infrastructure"
    / "cloud_function_knowledge_compiler"
)

sys.path.insert(0, str(FUNCTION_DIR))

from main import (
    SUPPORTED_FOLDERS,
    get_document_type,
    is_misplaced_syllabus,
    is_supported_document,
)


def test_knowledge_compiler_routes_by_gcs_prefix():
    assert get_document_type("curriculum/jee/mathematics/chapter-03.pdf") == "curriculum"
    assert get_document_type("syllabus/jee/jee-main.pdf") == "syllabus"
    assert get_document_type("raw-pdfs/question-bank.pdf") == "jee_raw_pdf"
    assert get_document_type("other/file.pdf") == "unknown"


def test_knowledge_compiler_accepts_curriculum_and_syllabus_prefixes():
    assert "curriculum/" in SUPPORTED_FOLDERS
    assert "syllabus/" in SUPPORTED_FOLDERS
    assert "raw-pdfs/" in SUPPORTED_FOLDERS


def test_knowledge_compiler_detects_misplaced_syllabus_pdf():
    assert is_misplaced_syllabus("curriculum/jee/mathematics/syllabus.pdf")
    assert not is_misplaced_syllabus("syllabus/jee/jee-main.pdf")
    assert not is_misplaced_syllabus("curriculum/jee/mathematics/chapter-03.pdf")


def test_knowledge_compiler_accepts_open_document_only_for_syllabus():
    assert is_supported_document("syllabus/jee/jee-main.odf")
    assert is_supported_document("syllabus/jee/jee-main.odt")
    assert is_supported_document("syllabus/jee/jee-main.pdf")
    assert not is_supported_document("curriculum/jee/mathematics/chapter-03.odf")
    assert is_supported_document("curriculum/jee/mathematics/chapter-03.pdf")
