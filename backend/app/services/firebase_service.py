import os
from typing import Any

# ✅ Correct path based on your structure
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "core", "firebase_key.json")
FIREBASE_ENABLED = os.getenv("MATHVERSE_ENABLE_FIREBASE", "").lower() in {"1", "true", "yes"}

db = None
_local_evaluation_records: list[dict[str, Any]] = []


def _get_db():
    if not FIREBASE_ENABLED:
        raise RuntimeError("Firebase is disabled. Set MATHVERSE_ENABLE_FIREBASE=true after fixing firebase_key.json.")

    global db
    if db is not None:
        return db

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    return db


def save_homework(homework: dict):
    if not FIREBASE_ENABLED:
        return

    _get_db().collection("homeworks").add(homework)


def get_homework(student_id: str):
    if not FIREBASE_ENABLED:
        return []

    docs = _get_db().collection("homeworks") \
        .where("student_id", "==", student_id) \
        .stream()

    return [doc.to_dict() for doc in docs]


def save_attempt(attempt: dict[str, Any]):
    if not FIREBASE_ENABLED:
        return

    _get_db().collection("attempts").add(attempt)


def get_attempts(student_id: str, limit: int = 100):
    if not FIREBASE_ENABLED:
        return []

    query = (
        _get_db()
        .collection("attempts")
        .where("student_id", "==", student_id)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in query]


def save_evaluation_record(record: dict[str, Any]) -> None:
    if FIREBASE_ENABLED:
        _get_db().collection("evaluation_records").add(record)
        return

    _local_evaluation_records.append(record)


def get_evaluation_records_by_test(test_id: str, limit: int = 1000) -> list[dict[str, Any]]:
    if FIREBASE_ENABLED:
        query = (
            _get_db()
            .collection("evaluation_records")
            .where("test_id", "==", test_id)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in query]

    return [record for record in _local_evaluation_records if record.get("test_id") == test_id][:limit]


def get_evaluation_records_by_student(student_id: str, limit: int = 1000) -> list[dict[str, Any]]:
    if FIREBASE_ENABLED:
        query = (
            _get_db()
            .collection("evaluation_records")
            .where("student_id", "==", student_id)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in query]

    return [record for record in _local_evaluation_records if record.get("student_id") == student_id][:limit]
