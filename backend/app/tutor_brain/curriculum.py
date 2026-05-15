from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.services.firebase_service import _get_db


LOCAL_CURRICULUM_DIR = Path(__file__).resolve().parents[1] / "data" / "curriculum"


def _load_local_curriculum(grade: int, exam: str = "cbse") -> dict:
    candidates = [
        LOCAL_CURRICULUM_DIR / f"{exam}_{grade}.json",
        LOCAL_CURRICULUM_DIR / "cbse_10.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return payload
        except Exception as error:
            print(f"Local curriculum read failed ({path.name}): {error}")
    return {}


def get_grade_curriculum(grade: int, exam: str = "cbse") -> dict:
    """Fetch grade+exam curriculum from Firestore, with local JSON fallback."""
    try:
        db = _get_db()
        doc_ref = db.collection("curriculums").document(f"{exam}_{grade}")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if isinstance(data, dict):
                return data
        print(f"Firestore curriculum missing for {exam}_{grade}. Using local fallback.")
        return _load_local_curriculum(grade, exam)
    except Exception as error:
        print(f"Firestore fetch failed: {error}")
        return _load_local_curriculum(grade, exam)


def list_chapters(grade: int, exam: str = "cbse") -> List[dict]:
    return get_grade_curriculum(grade, exam).get("chapters", [])


def get_default_topic_slug(grade: int, exam: str = "cbse") -> str:
    return get_grade_curriculum(grade, exam).get("default_topic_slug", "")


def get_topic(grade: int, topic_slug: Optional[str] = None, exam: str = "cbse") -> Optional[dict]:
    slug = topic_slug or get_default_topic_slug(grade, exam)
    for chapter in list_chapters(grade, exam):
        if chapter.get("slug") == slug:
            return chapter
    return None


def get_topic_concepts(grade: int, topic_slug: str, exam: str = "cbse") -> List[dict]:
    topic = get_topic(grade, topic_slug, exam)
    return topic.get("concepts", []) if topic else []


def get_concept(grade: int, topic_slug: str, concept_id: Optional[str] = None, exam: str = "cbse") -> Optional[dict]:
    concepts = get_topic_concepts(grade, topic_slug, exam)
    if not concepts:
        return None
    if concept_id is None:
        return concepts[0]
    for concept in concepts:
        if concept.get("id") == concept_id:
            return concept
    return None
