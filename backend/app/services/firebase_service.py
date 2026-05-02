import os
from typing import Any

# ✅ Correct path based on your structure
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "core", "firebase_key.json")

db = None


def _get_db():
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
    _get_db().collection("homeworks").add(homework)


def get_homework(student_id: str):
    docs = _get_db().collection("homeworks") \
        .where("student_id", "==", student_id) \
        .stream()

    return [doc.to_dict() for doc in docs]


def save_attempt(attempt: dict[str, Any]):
    _get_db().collection("attempts").add(attempt)


def get_attempts(student_id: str, limit: int = 100):
    query = (
        _get_db()
        .collection("attempts")
        .where("student_id", "==", student_id)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in query]
