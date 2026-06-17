"""
Firestore-backed CBSE exercise and theory retrieval.

This module provides Firestore alternatives to local PDF extraction, with
fallback support for gradual migration from local PDFs to Firestore storage.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional

try:
    from app.core.firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client
except ImportError:
    from backend.app.core.firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client

# Firestore collections
CBSE_EXERCISES_COLLECTION = "cbse_practice_problems"
CBSE_THEORY_COLLECTION = "cbse_theory_content"

# Environment flag for enabling Firestore-first retrieval
USE_FIRESTORE_EXERCISES = os.getenv("MATHVERSE_EXERCISES_SOURCE", "local").strip().lower() == "firestore"


@lru_cache(maxsize=1)
def _firestore_module():
    from google.cloud import firestore

    return firestore


@lru_cache(maxsize=1)
def _firestore_client():
    """Get the Firestore client."""
    return get_firestore_client()


def _build_exercise_doc_id(grade: int, chapter_index: int) -> str:
    """Build a document ID for exercise storage."""
    return f"grade_{grade}_chapter_{chapter_index:02d}"


def _build_theory_doc_id(grade: int, chapter_index: int) -> str:
    """Build a document ID for theory storage."""
    return f"grade_{grade}_chapter_{chapter_index:02d}_theory"


def load_chapter_firestore_exercises(
    grade: int,
    chapter_index: int,
    chapter_title: str,
) -> list[dict[str, Any]]:
    """
    Load exercise problems from Firestore.
    
    Args:
        grade: Student grade (e.g., 10)
        chapter_index: Chapter number (e.g., 1 for Real Numbers)
        chapter_title: Chapter title (e.g., "Real Numbers")
    
    Returns:
        List of problem dictionaries with keys: chapter_index, chapter_title, 
        exercise, number, prompt, source_file, figure_hint, source.
    """
    try:
        db = _firestore_client()
        doc_id = _build_exercise_doc_id(grade, chapter_index)
        doc_ref = db.collection(CBSE_EXERCISES_COLLECTION).document(doc_id)
        doc = doc_ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS)
        
        if not doc.exists:
            return []
        
        data = doc.to_dict() or {}
        
        # Extract problems from the document
        problems = data.get("problems", [])
        if not isinstance(problems, list):
            return []
        
        # Ensure each problem has required fields and correct source
        for problem in problems:
            problem["chapter_index"] = chapter_index
            problem["chapter_title"] = chapter_title
            problem["source"] = "cbse_firestore_exercise"
        
        return problems
    
    except Exception as e:
        print(f"Error loading Firestore exercises for grade {grade} chapter {chapter_index}: {e}")
        return []


def load_chapter_firestore_theory(grade: int, chapter_index: int) -> str:
    """
    Load theory content from Firestore.
    
    Args:
        grade: Student grade (e.g., 10)
        chapter_index: Chapter number
    
    Returns:
        Theory text or empty string if not found.
    """
    try:
        db = _firestore_client()
        doc_id = _build_theory_doc_id(grade, chapter_index)
        doc_ref = db.collection(CBSE_THEORY_COLLECTION).document(doc_id)
        doc = doc_ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS)
        
        if not doc.exists:
            return ""
        
        data = doc.to_dict() or {}
        return data.get("content", "")
    
    except Exception as e:
        print(f"Error loading Firestore theory for grade {grade} chapter {chapter_index}: {e}")
        return ""


def store_chapter_exercises(
    grade: int,
    chapter_index: int,
    chapter_title: str,
    problems: list[dict[str, Any]],
) -> bool:
    """
    Store exercise problems in Firestore.
    
    Args:
        grade: Student grade (e.g., 10)
        chapter_index: Chapter number
        chapter_title: Chapter title
        problems: List of problem dictionaries
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        db = _firestore_client()
        doc_id = _build_exercise_doc_id(grade, chapter_index)
        
        doc_data = {
            "grade": grade,
            "chapter_index": chapter_index,
            "chapter_title": chapter_title,
            "problems": problems,
            "problem_count": len(problems),
        }
        
        db.collection(CBSE_EXERCISES_COLLECTION).document(doc_id).set(doc_data)
        return True
    
    except Exception as e:
        print(f"Error storing Firestore exercises for grade {grade} chapter {chapter_index}: {e}")
        return False


def store_chapter_theory(
    grade: int,
    chapter_index: int,
    content: str,
) -> bool:
    """
    Store theory content in Firestore.
    
    Args:
        grade: Student grade (e.g., 10)
        chapter_index: Chapter number
        content: Theory text
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        db = _firestore_client()
        doc_id = _build_theory_doc_id(grade, chapter_index)
        
        doc_data = {
            "grade": grade,
            "chapter_index": chapter_index,
            "content": content,
            "content_length": len(content),
        }
        
        db.collection(CBSE_THEORY_COLLECTION).document(doc_id).set(doc_data)
        return True
    
    except Exception as e:
        print(f"Error storing Firestore theory for grade {grade} chapter {chapter_index}: {e}")
        return False


def delete_chapter_exercises(grade: int, chapter_index: int) -> bool:
    """Delete exercise problems from Firestore."""
    try:
        db = _firestore_client()
        doc_id = _build_exercise_doc_id(grade, chapter_index)
        db.collection(CBSE_EXERCISES_COLLECTION).document(doc_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting Firestore exercises: {e}")
        return False


def delete_chapter_theory(grade: int, chapter_index: int) -> bool:
    """Delete theory content from Firestore."""
    try:
        db = _firestore_client()
        doc_id = _build_theory_doc_id(grade, chapter_index)
        db.collection(CBSE_THEORY_COLLECTION).document(doc_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting Firestore theory: {e}")
        return False


def list_available_chapters(grade: int) -> dict[int, dict[str, Any]]:
    """
    List all available chapters in Firestore for a grade.
    
    Returns:
        Dict mapping chapter_index to metadata {chapter_title, problem_count}.
    """
    try:
        db = _firestore_client()
        chapters = {}
        
        firestore = _firestore_module()
        docs = db.collection(CBSE_EXERCISES_COLLECTION).where(
            filter=firestore.FieldFilter("grade", "==", grade)
        ).stream(timeout=FIRESTORE_TIMEOUT_SECONDS)
        
        for doc in docs:
            data = doc.to_dict() or {}
            chapter_index = data.get("chapter_index")
            if chapter_index is not None:
                chapters[chapter_index] = {
                    "title": data.get("chapter_title", f"Chapter {chapter_index}"),
                    "problem_count": data.get("problem_count", 0),
                }
        
        return chapters
    
    except Exception as e:
        print(f"Error listing chapters: {e}")
        return {}
