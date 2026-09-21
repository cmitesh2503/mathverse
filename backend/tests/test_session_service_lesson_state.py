
from app.models.session import StartSessionRequest
from app.services.session_service import SessionService


def test_update_lesson_state(tmp_path):
    service = SessionService(
        store_path=tmp_path / "class_sessions.json"
    )

    request = StartSessionRequest(
        student_id="student-1",
        grade=10,
        board="CBSE",
        subject="Mathematics",
        topic_slug="real_numbers",
        start_new=True,
    )

    session = service.create_or_resume_session(request)

    updated = service.update_lesson_state(
        session.session_id,
        lesson_id="real-numbers-lesson-1",
        current_concept="Euclid's Division Lemma",
        concept_index=2,
        lesson_stage="worked_example",
    )

    assert updated is not None
    assert updated.lesson_id == "real-numbers-lesson-1"
    assert updated.current_concept == "Euclid's Division Lemma"
    assert updated.concept_index == 2
    assert updated.lesson_stage == "worked_example"

    reloaded = service.get_session(session.session_id)

    assert reloaded is not None
    assert reloaded.lesson_id == "real-numbers-lesson-1"
    assert reloaded.current_concept == "Euclid's Division Lemma"
    assert reloaded.concept_index == 2
    assert reloaded.lesson_stage == "worked_example"


def test_update_lesson_state_does_not_accept_negative_concept_index(tmp_path):
    service = SessionService(
        store_path=tmp_path / "class_sessions.json"
    )

    request = StartSessionRequest(
        student_id="student-2",
        grade=10,
        board="CBSE",
        subject="Mathematics",
        topic_slug="real_numbers",
        start_new=True,
    )

    session = service.create_or_resume_session(request)

    service.update_lesson_state(
        session.session_id,
        concept_index=3,
    )

    updated = service.update_lesson_state(
        session.session_id,
        concept_index=-1,
    )

    assert updated is not None
    assert updated.concept_index == 3


def test_update_lesson_state_returns_none_for_missing_session(tmp_path):
    service = SessionService(
        store_path=tmp_path / "class_sessions.json"
    )

    result = service.update_lesson_state(
        "missing-session",
        lesson_id="lesson-1",
        current_concept="Euclid's Division Lemma",
        concept_index=1,
        lesson_stage="concept_explanation",
    )

    assert result is None