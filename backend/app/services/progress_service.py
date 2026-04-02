from ..core.storage.firebase_client import db
from datetime import datetime

def save_progress(student_id, question, correct, hints_used):
    data = {
        "student_id": student_id,
        "question": question,
        "correct": correct,
        "hints_used": hints_used,
        "timestamp": datetime.utcnow()
    }

    db.collection("attempts").add(data)