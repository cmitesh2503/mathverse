from functools import lru_cache

from ..core.firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client

# 1. Initialize GCP Clients


@lru_cache(maxsize=1)
def _firestore_module():
    from google.cloud import firestore

    return firestore


@lru_cache(maxsize=1)
def _vector_class():
    from google.cloud.firestore_v1.vector import Vector

    return Vector


@lru_cache(maxsize=1)
def _firestore_client():
    return get_firestore_client()


def _collection_ref():
    return _firestore_client().collection("pdf_chunks")

@lru_cache(maxsize=1)
def _embedding_model():
    from vertexai.language_models import TextEmbeddingModel

    return TextEmbeddingModel.from_pretrained("text-embedding-004")

def get_query_embedding(text: str) -> list[float]:
    """Converts text into a vector embedding."""
    embeddings = _embedding_model().get_embeddings([text])
    return embeddings[0].values

def retrieve_context(query: str, grade: str, chapter: str, top_k: int = 4) -> str:
    """
    Searches Firestore for the most relevant textbook chunks 
    based on the student's exact question and current chapter.
    """
    try:
        firestore = _firestore_module()
        Vector = _vector_class()

        # Convert the student's question into a vector
        query_vector = get_query_embedding(query)

        # Native Vector Search on Firestore bounded by Grade and Chapter
        docs = _collection_ref().where(
            filter=firestore.FieldFilter("metadata.grade", "==", grade)
        ).where(
            filter=firestore.FieldFilter("metadata.chapter", "==", chapter)
        ).find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_vector),
            distance_measure=firestore.DistanceMeasure.COSINE,
            limit=top_k
        ).stream(timeout=FIRESTORE_TIMEOUT_SECONDS)

        # Compile the retrieved chunks into a single context string
        context_chunks = []
        for doc in docs:
            data = doc.to_dict()
            context_chunks.append(data.get("text", ""))

        if not context_chunks:
            return "No specific curriculum context found for this topic."

        return "\n\n---\n\n".join(context_chunks)

    except Exception as e:
        print(f"Error retrieving context from Firestore: {e}")
        return ""

# --- BACKWARD COMPATIBILITY ALIASES ---
def embed_text(text: str) -> list[float]:
    """Exposes embedding generation for evaluation routes."""
    return get_query_embedding(text)

def get_context(query: str, grade: str, chapter: str, top_k: int = 4) -> str:
    """Exposes context retrieval for the proctor agent."""
    return retrieve_context(query, grade, chapter, top_k)
# ---------------------------------------
