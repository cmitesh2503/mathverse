from firebase_admin import firestore
from typing import List, Dict, Optional, Tuple
from app.services.firebase_service import _get_db
# --- CLOUD DATABASE LOADER ---
def get_grade_curriculum(grade: int, exam: str = "cbse") -> dict:
    """Fetches the specific grade and exam syllabus directly from Firestore."""
    try:
        # ✅ Safely get the database connection (this auto-initializes Firebase!)
        db = _get_db() 
        
        doc_ref = db.collection("curriculums").document(f"{exam}_{grade}")
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"⚠️ Warning: {exam}_{grade} not found in Firestore. Using fallback.")
            # Fallback to a default if the specific grade isn't found
            fallback = db.collection("curriculums").document("cbse_10").get()
            return fallback.to_dict() if fallback.exists else {}
            
    except Exception as e:
        print(f"🔥 Firestore Fetch Error: {e}")
        return {}
# --- HELPER FUNCTIONS ---
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