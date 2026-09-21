from app.models.session import StartSessionRequest
from app.services.session_service import SessionService


def test_serialize_session_exposes_lesson_state(tmp_path):
    service = SessionService(
        store_path=tmp_path / "class_sessions.json"
    )

    request = StartSessionRequest(
        student_id="student-serialization-1",
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

    payload = service.serialize_session(updated)

    assert payload["lesson_id"] == "real-numbers-lesson-1"
    assert payload["current_concept"] == "Euclid's Division Lemma"
    assert payload["concept_index"] == 2
    assert payload["lesson_stage"] == "worked_example"


def test_serialize_session_preserves_default_lesson_state(tmp_path):
    service = SessionService(
        store_path=tmp_path / "class_sessions.json"
    )

    request = StartSessionRequest(
        student_id="student-serialization-2",
        grade=10,
        board="CBSE",
        subject="Mathematics",
        topic_slug="real_numbers",
        start_new=True,
    )

    session = service.create_or_resume_session(request)

    payload = service.serialize_session(session)

    assert payload["lesson_id"] == ""
    assert payload["current_concept"] == ""
    assert payload["concept_index"] == 0