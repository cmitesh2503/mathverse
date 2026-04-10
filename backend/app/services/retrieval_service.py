import json
import google.generativeai as genai
from ..core.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def load_chunks():
    with open("backend/app/data/ncert_chunks.json", "r") as f:
        return json.load(f)

def retrieve_context(topic: str, grade: int = None, n_results: int = 5) -> str:
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(name="cbse_curriculum")

        query_embedding = embed_text(topic)

        if grade is not None:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"grade": grade}
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