import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import Orchestrator
from app.core.guards import resolve_tutor_action_access_topic
from app.models.session import SessionPhase, StudentSession


def test_next_topic_inside_free_chapter_resolves_to_current_chapter():
    session = StudentSession(
        grade=10,
        exam="cbse",
        chapter_name="Real Numbers",
        current_chapter_index=0,
        current_topic_index=0,
        agenda=["Euclid's Division Lemma", "Revisiting HCF and LCM"],
    )

    assert (
        resolve_tutor_action_access_topic(
            session=session,
            action="next_topic",
            requested_grade=10,
            exam="cbse",
        )
        == "real_numbers"
    )


def test_next_topic_at_chapter_boundary_resolves_to_next_chapter():
    session = StudentSession(
        grade=10,
        exam="cbse",
        chapter_name="Real Numbers",
        current_chapter_index=0,
        current_topic_index=0,
        agenda=["Irrational Numbers"],
    )

    assert (
        resolve_tutor_action_access_topic(
            session=session,
            action="next_topic",
            requested_grade=10,
            exam="cbse",
        )
        == "polynomials"
    )


def test_continue_without_explicit_slug_resolves_to_current_paid_chapter():
    session = StudentSession(
        grade=10,
        exam="cbse",
        chapter_name="Polynomials",
        current_chapter_index=1,
        current_topic_index=0,
        agenda=["Polynomials"],
    )

    assert (
        resolve_tutor_action_access_topic(
            session=session,
            action="continue",
            requested_grade=10,
            exam="cbse",
        )
        == "polynomials"
    )


def test_chapter_advance_resets_theory_state_for_new_chapter():
    session = StudentSession(
        grade=10,
        exam="cbse",
        chapter_name="Real Numbers",
        current_chapter="Real Numbers",
        current_chapter_index=0,
        current_topic_index=0,
        agenda=["Irrational Numbers"],
        active_phase=SessionPhase.PRACTICE,
        current_phase=SessionPhase.PRACTICE.value,
        class_intro_done=True,
        concept_teaching_index=4,
        concept_teaching_complete=True,
        exercise_phase_started=True,
        next_problem_actions=[{"action": "draw_text", "content": "stale"}],
    )

    next_topic = Orchestrator()._advance_to_next_topic(session)

    assert next_topic == "Polynomials"
    assert session.chapter_name == "Polynomials"
    assert session.current_chapter == "Polynomials"
    assert session.current_chapter_index == 1
    assert session.active_phase == SessionPhase.TEACHING
    assert session.current_phase == SessionPhase.TEACHING.value
    assert not session.class_intro_done
    assert session.concept_teaching_index == 0
    assert not session.concept_teaching_complete
    assert not session.exercise_phase_started
    assert session.next_problem_actions == []
