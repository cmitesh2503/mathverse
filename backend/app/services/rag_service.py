import os
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from vertexai.language_models import TextEmbeddingModel

# 1. Initialize GCP Clients
PROJECT_ID = os.environ.get("PROJECT_ID", "mathverse-live-ai")
db = firestore.Client(project=PROJECT_ID)
collection_ref = db.collection("pdf_chunks")

# 2. Initialize the exact same Embedding Model used in the Cloud Function
EMBEDDING_MODEL = TextEmbeddingModel.from_pretrained("text-embedding-004")

def get_query_embedding(text: str) -> list[float]:
    """Converts text into a vector embedding."""
    embeddings = EMBEDDING_MODEL.get_embeddings([text])
    return embeddings[0].values

def retrieve_context(query: str, grade: str, chapter: str, top_k: int = 4) -> str:
    """
    Searches Firestore for the most relevant textbook chunks 
    based on the student's exact question and current chapter.
    """
    try:
        # Convert the student's question into a vector
        query_vector = get_query_embedding(query)

        # Native Vector Search on Firestore bounded by Grade and Chapter
        docs = collection_ref.where(
            filter=firestore.FieldFilter("metadata.grade", "==", grade)
        ).where(
            filter=firestore.FieldFilter("metadata.chapter", "==", chapter)
        ).find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_vector),
            distance_measure=firestore.DistanceMeasure.COSINE,
            limit=top_k
        ).stream()

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