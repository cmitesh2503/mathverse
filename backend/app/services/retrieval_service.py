import json
from pathlib import Path

import google.generativeai as genai

from ..core.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

CHUNKS_PATH = Path(__file__).resolve().parents[1] / "data" / "ncert_chunks.json"

def load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return json.load(f)

def retrieve_context(topic: str, grade: int = None, n_results: int = 5, metadata_filter: dict | None = None) -> str:
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(name="cbse_curriculum")

        query_embedding = embed_text(topic)
        where_clause = {}
        if grade is not None:
            where_clause["grade"] = grade
        if metadata_filter:
            for key, value in metadata_filter.items():
                if value is not None and value != "":
                    where_clause[key] = value

        if where_clause:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause
            )
        else:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

        documents = results.get("documents", [])
        if documents:
            return "\n\n".join(documents)
        return ""
    except Exception:
        # Fallback to old method
        chunks = load_chunks()
        results = [c["text"] for c in chunks if c.get("topic") == topic]
        return "\n\n".join(results[:n_results])

def embed_text(text):
    result = genai.embed_content(
        model="models/embedding-001",
        content=text
    )
    return result['embedding']
