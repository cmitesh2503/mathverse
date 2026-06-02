import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import tutor
from app.models.session import StudentSession


def test_broken_tree_diagram_uses_vertical_tree_and_ground_base():
    prompt = (
        "A tree breaks due to storm and the broken part bends so that the top of the tree "
        "touches the ground making an angle 30° with it. The distance between the foot of "
        "the tree to the point where the top touches the ground is 8 m."
    )
    steps = [
        "Let BC = x be the remaining standing part.",
        "Identify the right-angled triangle BCD where angle BDC = 30° and CD = 8 m.",
    ]

    actions = tutor._solution_actions(
        exercise_label="Exercise 9.1",
        problem_number="2",
        prompt=prompt,
        solved_steps=steps,
        answer="8√3 m",
        source_label="test",
        diagram_hint="Draw the broken tree diagram with foot C, break point B, and top touching ground at D.",
    )
    diagram_actions = [
        action
        for action in actions
        if isinstance(action.get("metadata"), dict) and action["metadata"].get("diagram")
    ]
    step_lines = [action.get("content", "") for action in actions if action.get("action") == "draw_text"]

    assert any(action.get("action") == "draw_line" and action.get("label") == "BC = x" and action.get("x1") == action.get("x2") for action in diagram_actions)
    assert any(action.get("action") == "draw_line" and action.get("label") == "CD = 8 m" and action.get("y1") == action.get("y2") for action in diagram_actions)
    assert any(action.get("action") == "draw_angle" and action.get("label") == "30°" for action in diagram_actions)
    assert "Read the problem carefully" in step_lines[3]
    assert "We need to find" in step_lines[4]


def test_problem_readout_and_voice_chunks_use_spoken_explanation_not_board_steps():
    steps = [
        "Exercise no: Exercise 9.1",
        "Problem no: 2: A tree breaks and makes x² with the ground. Find the height.",
        "Solution:",
        "Step 1: Draw segment CD.",
    ]

    spoken = tutor._spoken_from_steps("", steps, "Applications of Trigonometry", "en-IN")
    chunks = tutor._voice_chunks_from_steps(spoken, steps)

    assert "First, let us read the question carefully" in spoken
    assert "squared" in " ".join(chunks)
    assert not chunks[0].startswith("Step 1")


def test_header_normalization_replaces_generic_tree_triangle_with_measured_diagram():
    prompt = (
        "A tree breaks due to storm and the broken part bends so that the top of the tree "
        "touches the ground making an angle 30° with it. The distance between the foot of "
        "the tree to the point where the top touches the ground is 8 m. Find the height."
    )
    old_actions = [
        {"action": "draw_text", "content": "Exercise no: Exercise 9.1"},
        {"action": "draw_text", "content": f"Problem no: 2: {prompt}"},
        {"action": "draw_text", "content": "Solution:"},
        {"action": "draw_line", "x1": 34, "y1": 136, "x2": 260, "y2": 136, "label": "CD", "metadata": {"diagram": True}},
        {"action": "draw_line", "x1": 34, "y1": 136, "x2": 120, "y2": 24, "label": "BC", "metadata": {"diagram": True}},
        {"action": "draw_line", "x1": 120, "y1": 24, "x2": 260, "y2": 136, "label": "BD", "metadata": {"diagram": True}},
        {"action": "draw_text", "content": "Step 1: Draw segment CD."},
    ]
    session = StudentSession(grade=10, exam="cbse", chapter_name="Some Applications of Trigonometry")

    normalized = tutor._ensure_problem_headers(session, old_actions, fallback_problem_no="2")
    diagram_actions = [
        action
        for action in normalized
        if isinstance(action.get("metadata"), dict) and action["metadata"].get("diagram")
    ]
    step_lines = [action.get("content", "") for action in normalized if action.get("action") == "draw_text"]

    assert any(action.get("label") == "CD = 8 m" for action in diagram_actions)
    assert any(action.get("action") == "draw_angle" and action.get("label") == "30°" for action in diagram_actions)
    assert any("Read the problem carefully" in line for line in step_lines)


def test_chapter_start_teaches_pdf_theory_before_exercises(monkeypatch):
    theory_text = (
        "In this chapter, we shall study some ways in which trigonometry is used in the life around you. "
        "Heights and distances can be found by forming a right triangle and using trigonometric ratios. "
        "The line drawn from the eye of the observer to the point in the object viewed by the observer is called the line of sight. "
        "The angle of elevation is the angle formed by the line of sight with the horizontal when the object is above the horizontal level. "
        "Therefore, when a distance on the ground is known and the angle of elevation is known, tan theta connects height and distance. "
        "For example, the height of a tower or tree can be found by drawing a right triangle and marking the unknown height as x."
    )

    monkeypatch.setattr(
        tutor,
        "_chapter_for_session",
        lambda session: {
            "title": "Some Applications of Trigonometry",
            "slug": "applications_of_trigonometry",
            "book_topics": ["Heights and Distances"],
        },
    )

    import app.services.cbse_exercises as cbse_exercises

    monkeypatch.setattr(cbse_exercises, "load_chapter_pdf_theory", lambda grade, chapter_no: theory_text)
    monkeypatch.setattr(cbse_exercises, "_chapter_pdf_path", lambda grade, chapter_no, phase: None)

    session = StudentSession(
        grade=10,
        exam="cbse",
        chapter_name="Some Applications of Trigonometry",
        current_chapter="Some Applications of Trigonometry",
        current_phase="teaching",
    )

    actions = tutor._chapter_teaching_phase_actions(session, rag_context="")
    board_text = [action.get("content", "") for action in actions if action.get("action") == "draw_text"]

    assert any("Theory:" in line and "trigonometric ratios" in line for line in board_text)
    assert any(line.startswith("Explanation:") for line in board_text)
    assert any(line.startswith("Reasoning:") for line in board_text)
    assert any(line.startswith("Worked example:") for line in board_text)
    assert not any("Today's flow" in line or "Topics in this chapter" in line for line in board_text)
    assert not any(line.startswith("Problem no:") for line in board_text)
    assert not session.exercise_phase_started


def test_theory_first_flow_is_not_limited_to_grade_10_trigonometry(monkeypatch):
    theory_text = (
        "A set is a well-defined collection of objects. "
        "The objects in a set are called its elements. "
        "Sets are usually denoted by capital letters and their elements are written inside braces. "
        "Therefore, to describe a set correctly, we must know exactly whether an object belongs to it or not. "
        "For example, the set of natural numbers less than 5 is written as A = {1, 2, 3, 4}."
    )

    monkeypatch.setattr(
        tutor,
        "_chapter_for_session",
        lambda session: {
            "title": "Sets",
            "slug": "sets",
            "book_topics": ["Set notation and representations"],
        },
    )

    import app.services.cbse_exercises as cbse_exercises

    monkeypatch.setattr(cbse_exercises, "load_chapter_pdf_theory", lambda grade, chapter_no: theory_text)
    monkeypatch.setattr(cbse_exercises, "_chapter_pdf_path", lambda grade, chapter_no, phase: None)

    session = StudentSession(
        grade=11,
        exam="jee",
        chapter_name="Sets",
        current_chapter="Sets",
        current_phase="teaching",
    )

    actions = tutor._chapter_teaching_phase_actions(session, rag_context="")
    board_text = [action.get("content", "") for action in actions if action.get("action") == "draw_text"]

    assert any("Theory:" in line and "well-defined collection" in line for line in board_text)
    assert any("Explanation:" in line and "elements" in line for line in board_text)
    assert any("Worked example:" in line and "{1, 2, 3, 4}" in line for line in board_text)
    assert not any(line.startswith("Problem no:") for line in board_text)
    assert not session.exercise_phase_started
