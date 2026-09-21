from app.tutor_brain.tutor_engine import ClassroomState, TutorEngine


def test_hydrate_lesson_state():
    engine = TutorEngine()

    state = ClassroomState(
        grade=10,
        topic_slug="real_numbers",
    )

    session = type(
        "Session",
        (),
        {
            "grade": 10,
            "active_phase": "teaching",
            "lesson_stage": "worked_example",
            "lesson_id": "real-numbers-lesson-1",
            "current_concept": "Euclid's Division Lemma",
            "concept_index": 2,
            "topic_slug": "real_numbers",
            "metadata": {},
            "lesson_notes": [],
            "summary": "",
        },
    )()

    engine._states["test-session"] = state
    engine.hydrate_session("test-session", session)

    hydrated = engine._states["test-session"]

    assert hydrated.lesson_id == "real-numbers-lesson-1"
    assert hydrated.current_concept == "Euclid's Division Lemma"
    assert hydrated.current_concept_index == 2
    assert hydrated.stage == "worked_example"