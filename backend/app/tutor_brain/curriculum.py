from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.services.firebase_service import _get_db
from app.services.cbse_exercises import (
    GRADE_10_PDF_CHAPTERS,
    load_chapter_pdf_exercises,
)


LOCAL_CURRICULUM_DIR = Path(__file__).resolve().parents[1] / "data" / "curriculum"
CBSE10_CHAPTER_TITLES: dict[str, str] = {
    "real_numbers": "Real Numbers",
    "polynomials": "Polynomials",
    "pair_of_linear_equations": "Pair of Linear Equations in Two Variables",
    "quadratic_equations": "Quadratic Equations",
    "arithmetic_progressions": "Arithmetic Progressions",
    "triangles": "Triangles",
    "coordinate_geometry": "Coordinate Geometry",
    "introduction_to_trigonometry": "Introduction to Trigonometry",
    "applications_of_trigonometry": "Some Applications of Trigonometry",
    "circles": "Circles",
    "constructions": "Constructions",
    "areas_related_to_circles": "Areas Related to Circles",
    "surface_areas_and_volumes": "Surface Areas and Volumes",
    "statistics": "Statistics",
    "probability": "Probability",
}


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

def _augment_curriculum_from_pdf(payload: dict, grade: int, exam: str) -> dict:
    if not isinstance(payload, dict):
        return payload
    if str(exam or "").lower() != "cbse" or int(grade or 0) != 10:
        return payload

    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        chapters = []

    existing_slugs = {str(item.get("slug") or "").strip() for item in chapters if isinstance(item, dict)}
    for slug, chapter_no in sorted(GRADE_10_PDF_CHAPTERS.items(), key=lambda item: item[1]):
        if chapter_no <= 0 or slug in existing_slugs:
            continue
        title = CBSE10_CHAPTER_TITLES.get(slug, slug.replace("_", " ").title())
        pdf_examples = load_chapter_pdf_exercises(10, chapter_no, title)
        chapter_obj = {
            "slug": slug,
            "title": title,
            "summary": f"NCERT Class 10 Chapter {chapter_no}: {title}",
            "book_topics": [title],
            "concepts": [
                {
                    "id": f"{slug}_pdf_exercises",
                    "title": f"{title} Exercises",
                    "definition": f"Practice problems from NCERT Chapter {chapter_no}.",
                    "explanation": "Solve textbook exercises step by step and justify each step.",
                    "board_work": [
                        "Read the problem carefully.",
                        "Identify theorem/formula and known values.",
                        "Solve step by step and verify final answer.",
                    ],
                    "ncert_examples": [
                        {
                            "prompt": problem.get("prompt"),
                            "rule_used": "NCERT textbook exercise",
                            "steps": [],
                        }
                        for problem in pdf_examples[:30]
                        if isinstance(problem, dict) and str(problem.get("prompt") or "").strip()
                    ],
                }
            ],
        }
        chapters.append(chapter_obj)

    payload["chapters"] = chapters
    return payload


def get_grade_curriculum(grade: int, exam: str = "cbse") -> dict:
    """Fetch grade+exam curriculum from Firestore, with local JSON fallback."""
    try:
        db = _get_db()
        doc_ref = db.collection("curriculums").document(f"{exam}_{grade}")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if isinstance(data, dict):
                return _augment_curriculum_from_pdf(data, grade, exam)
        print(f"Firestore curriculum missing for {exam}_{grade}. Using local fallback.")
        return _augment_curriculum_from_pdf(_load_local_curriculum(grade, exam), grade, exam)
    except Exception as error:
        print(f"Firestore fetch failed: {error}")
        return _augment_curriculum_from_pdf(_load_local_curriculum(grade, exam), grade, exam)


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
