import firebase_admin
from firebase_admin import credentials, firestore
import os

# ✅ Correct path based on your structure
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "core", "firebase_key.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


def save_homework(homework: dict):
    db.collection("homeworks").add(homework)


def get_homework(student_id: str):
    docs = db.collection("homeworks") \
        .where("student_id", "==", student_id) \
        .stream()

    return [doc.to_dict() for doc in docs]