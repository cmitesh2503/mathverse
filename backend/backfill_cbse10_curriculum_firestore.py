from __future__ import annotations

from app.services.firebase_service import _get_db
from app.tutor_brain.curriculum import get_grade_curriculum


def run() -> None:
    db = _get_db()
    payload = get_grade_curriculum(10, "cbse")
    db.collection("curriculums").document("cbse_10").set(payload)
    chapter_count = len(payload.get("chapters", [])) if isinstance(payload, dict) else 0
    print(f"Updated curriculums/cbse_10 with {chapter_count} chapters.")


if __name__ == "__main__":
    run()
