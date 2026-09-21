from app.services.student_session_manager import StudentSessionManager
from app.services.student_session_model import LessonStage


def test_start_lesson():
    manager = StudentSessionManager()
    session = manager.get_session("test-question", "Real Numbers")

    manager.start_lesson(
        session,
        "lesson-1",
        "Euclid Division Lemma"
    )

    assert session.lesson_id == "lesson-1"
    assert session.concept_index == 0
    assert session.current_concept == "Euclid Division Lemma"
    assert session.lesson_stage == LessonStage.CHAPTER_INTRO


def test_set_current_concept():
    manager = StudentSessionManager()
    session = manager.get_session("test-question", "Real Numbers")

    manager.start_lesson(
        session,
        "lesson-1",
        "Euclid Division Lemma"
    )

    manager.set_current_concept(
        session,
        "Fundamental Theorem of Arithmetic"
    )

    assert session.current_concept == "Fundamental Theorem of Arithmetic"
    assert session.concept_index == 0
    assert session.lesson_stage == LessonStage.CHAPTER_INTRO


def test_advance_lesson_stage():
    manager = StudentSessionManager()
    session = manager.get_session("test-question", "Real Numbers")

    manager.start_lesson(
        session,
        "lesson-1",
        "Euclid Division Lemma"
    )

    expected_stages = [
        LessonStage.CONCEPT_EXPLANATION,
        LessonStage.UNDERSTANDING_CHECK,
        LessonStage.WORKED_EXAMPLE,
        LessonStage.STUDENT_PRACTICE,
        LessonStage.EXERCISE,
        LessonStage.SUMMARY,
    ]

    for expected_stage in expected_stages:
        manager.advance_lesson_stage(session)
        assert session.lesson_stage == expected_stage


def test_summary_stage_is_terminal():
    manager = StudentSessionManager()
    session = manager.get_session("test-question", "Real Numbers")

    manager.start_lesson(
        session,
        "lesson-1",
        "Euclid Division Lemma"
    )

    for _ in range(6):
        manager.advance_lesson_stage(session)

    assert session.lesson_stage == LessonStage.SUMMARY

    manager.advance_lesson_stage(session)

    assert session.lesson_stage == LessonStage.SUMMARY


def test_advance_concept():
    manager = StudentSessionManager()
    session = manager.get_session("test-question", "Real Numbers")

    manager.start_lesson(
        session,
        "lesson-1",
        "Euclid Division Lemma"
    )

    manager.advance_concept(session)

    assert session.concept_index == 1
    assert session.current_concept == "Euclid Division Lemma"

    manager.advance_concept(session)

    assert session.concept_index == 2
    assert session.current_concept == "Euclid Division Lemma"
