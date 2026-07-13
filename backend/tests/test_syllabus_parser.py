import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_factory.syllabus_parser import SyllabusParser


def test_parse_markdown_uses_jee_syllabus_source_path_metadata():
    markdown = """
    # JEE Main Mathematics Syllabus 2026

    ## Chapter 1: Relations and Functions
    Relations: Types of relations, reflexive, symmetric, transitive
    Functions: One-one, onto, composite functions

    ## Chapter 2: Inverse Trigonometric Functions
    Definition: Range, principal value branch
    """

    syllabus = SyllabusParser().parse_markdown(
        markdown,
        source_path="syllabus/jee/jee-main.pdf",
    )

    assert syllabus.syllabus_id == "jee_jee-main_mathematics"
    assert syllabus.board == "jee"
    assert syllabus.grade == "jee-main"
    assert syllabus.subject == "Mathematics"
    assert syllabus.version == "2026"
    assert [chapter.title for chapter in syllabus.chapters] == [
        "Relations and Functions",
        "Inverse Trigonometric Functions",
    ]
    assert syllabus.chapters[0].chapter_id == "chapter-01"
    assert syllabus.chapters[0].topics[0].title == "Relations"
    assert syllabus.chapters[0].topics[0].subtopics == [
        "Types of relations",
        "reflexive",
        "symmetric",
        "transitive",
    ]


def test_parse_accepts_azure_layout_content_and_table_chapters():
    azure_document = {
        "analyzeResult": {
            "content": """
            Joint Entrance Examination (Main) 2026 Mathematics
            <table>
              <tr><th>Unit</th><th>Name of Unit</th><th>Marks</th></tr>
              <tr><td>I</td><td>Number Systems</td><td>10</td></tr>
              <tr><td>II</td><td>Algebra</td><td>20</td></tr>
            </table>
            Rational numbers: terminating decimals, non-terminating decimals
            """
        }
    }

    syllabus = SyllabusParser().parse(
        azure_document,
        source_path="syllabus/jee/mathematics.pdf",
    )

    assert syllabus.board == "jee"
    assert syllabus.grade == "jee-main"
    assert [chapter.chapter_id for chapter in syllabus.chapters] == [
        "chapter-01",
        "chapter-02",
    ]
    assert [chapter.title for chapter in syllabus.chapters] == [
        "Number Systems",
        "Algebra",
    ]
    assert syllabus.chapters[1].topics[0].title == "Rational numbers"


def test_parse_jee_advanced_source_path_keeps_advanced_grade():
    markdown = """
    # JEE Advanced Mathematics Syllabus 2026

    ## Chapter 1: Algebra
    Complex numbers: algebra of complex numbers, modulus
    """

    syllabus = SyllabusParser().parse_markdown(
        markdown,
        source_path="syllabus/jee/jee-advanced.pdf",
    )

    assert syllabus.board == "jee"
    assert syllabus.grade == "jee-advanced"


def test_parse_direct_syllabus_odf_path_infers_board_from_content():
    markdown = """
    # Joint Entrance Examination (Main) 2026 Mathematics Syllabus

    ## Chapter 1: Matrices and Determinants
    Matrices: algebra of matrices, inverse of a matrix
    """

    syllabus = SyllabusParser().parse_markdown(
        markdown,
        source_path="syllabus/syllabus.odf",
    )

    assert syllabus.board == "jee"
    assert syllabus.grade == "jee-main"


def test_parse_jee_advanced_odf_path_uses_filename_for_grade():
    markdown = """
    # JEE Advanced Mathematics Syllabus 2026

    ## Chapter 1: Algebra
    Complex numbers: algebra of complex numbers, modulus
    """

    syllabus = SyllabusParser().parse_markdown(
        markdown,
        source_path="syllabus/jee/jee-advanced.odf",
    )

    assert syllabus.board == "jee"
    assert syllabus.grade == "jee-advanced"


def test_parse_combined_jee_syllabus_keeps_only_mathematics_section():
    markdown = """
    # Joint Entrance Examination (Main) 2026 Syllabus

    ## Mathematics
    Unit I: Sets, Relations and Functions
    Relations: reflexive, symmetric, transitive
    Unit II: Matrices and Determinants
    Matrices: algebra of matrices, inverse of a matrix

    ## Physics
    Unit I: Physics and Measurement
    Units: dimensions, errors

    ## Chemistry
    Unit I: Some Basic Concepts in Chemistry
    Mole concept: concentration, stoichiometry
    """

    syllabus = SyllabusParser().parse_markdown(
        markdown,
        source_path="syllabus/jee/jee-main.pdf",
    )

    assert syllabus.subject == "Mathematics"
    assert [chapter.title for chapter in syllabus.chapters] == [
        "Sets, Relations and Functions",
        "Matrices and Determinants",
    ]
    assert all(
        "Physics" not in chapter.title and "Chemistry" not in chapter.title
        for chapter in syllabus.chapters
    )
