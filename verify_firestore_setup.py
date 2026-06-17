#!/usr/bin/env python3
"""
Verify Firestore database setup for MathVerse RAG.

This script checks the Firebase project configured in backend/.env and writes
a temporary schema document to the configured RAG collection.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.core.firestore_client import get_firestore_client, resolve_firestore_project_id

RAG_COLLECTION = os.getenv("MATHVERSE_RAG_COLLECTION", "pdf_chunks")
db = get_firestore_client()


def verify_firestore_setup() -> bool:
    """Verify Firestore database and collection schema."""
    print("Verifying Firestore setup for MathVerse...")
    print(f"Project: {resolve_firestore_project_id()}")
    print(f"Collection: {RAG_COLLECTION}")

    try:
        test_doc = {
            "text": "Schema validation test document",
            "embedding": [0.1] * 768,
            "metadata": {
                "grade": "Grade10",
                "chapter": "ch_06",
                "doc_type": "theory",
                "source": "test_setup.pdf",
            },
        }

        collection_ref = db.collection(RAG_COLLECTION)
        doc_ref = collection_ref.document("schema_test_doc_001")
        doc_ref.set(test_doc)
        print(f"Wrote test document to {RAG_COLLECTION}")

        retrieved = doc_ref.get()
        if not retrieved.exists:
            print("Document not found after write")
            return False

        data = retrieved.to_dict()
        print("Read document back")
        print(f"   - Text field: {len(data.get('text', ''))} chars")
        print(f"   - Embedding dim: {len(data.get('embedding', []))}")
        print(f"   - Metadata: {data.get('metadata', {})}")

        doc_ref.delete()
        print("Cleaned up test document")

        docs = list(collection_ref.limit(5).stream())
        print(f"Sample documents in {RAG_COLLECTION}: {len(docs)}")
        print("Firestore setup verified successfully.")
        return True
    except Exception as error:
        print(f"Error verifying Firestore setup: {error}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_firestore_setup()
    raise SystemExit(0 if success else 1)
