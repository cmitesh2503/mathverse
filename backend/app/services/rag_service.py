import os
import re
import uuid
from functools import lru_cache
from typing import Any

from ..cache.cache_manager import get_cache, set_cache
from ..core.firestore_client import (
    FIRESTORE_TIMEOUT_SECONDS,
    get_firestore_client,
    resolve_firestore_project_id,
)

RAG_COLLECTION = "pdf_chunks"
# Migrated fallback default to the active stable generation model
EMBEDDING_MODEL_NAME = os.getenv("MATHVERSE_EMBEDDING_MODEL", "gemini-embedding-001")
VERTEX_AI_LOCATION = (
    os.getenv("GOOGLE_CLOUD_LOCATION")
    or os.getenv("VERTEX_AI_LOCATION")
    or os.getenv("GOOGLE_CLOUD_REGION")
    or "us-central1"
)
ALLOW_UNSCOPED_RAG_FALLBACK = os.getenv("MATHVERSE_RAG_ALLOW_UNSCOPED_FALLBACK", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
RAG_CACHE_TTL_SECONDS = int(os.getenv("MATHVERSE_RAG_CACHE_TTL_SECONDS", "3600"))

GRADE_10_CHAPTER_IDS = {
    "real numbers": "ch_01",
    "real_numbers": "ch_01",
    "polynomials": "ch_02",
    "pair of linear equations in two variables": "ch_03",
    "pair of linear equations": "ch_03",
    "pair_of_linear_equations": "ch_03",
    "quadratic equations": "ch_04",
    "quadratic_equations": "ch_04",
    "arithmetic progressions": "ch_05",
    "arithmetic_progressions": "ch_05",
    "triangles": "ch_06",
    "coordinate geometry": "ch_07",
    "coordinate_geometry": "ch_07",
    "introduction to trigonometry": "ch_08",
    "introduction_to_trigonometry": "ch_08",
    "some applications of trigonometry": "ch_09",
    "applications of trigonometry": "ch_09",
    "applications_of_trigonometry": "ch_09",
    "circles": "ch_10",
    "constructions": "ch_10",
    "areas related to circles": "ch_11",
    "areas_related_to_circles": "ch_11",
    "surface areas and volumes": "ch_12",
    "surface_areas_and_volumes": "ch_12",
    "statistics": "ch_13",
    "probability": "ch_14",
}


@lru_cache(maxsize=1)
def _firestore_module():
    from google.cloud import firestore
    return firestore


@lru_cache(maxsize=1)
def _vector_class():
    from google.cloud.firestore_v1.vector import Vector
    return Vector


@lru_cache(maxsize=1)
def _distance_measure_enum():
    from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
    return DistanceMeasure


@lru_cache(maxsize=1)
def _firestore_client():
    return get_firestore_client()


def _collection_ref():
    return _firestore_client().collection(RAG_COLLECTION)


@lru_cache(maxsize=1)
def _init_vertexai() -> None:
    import vertexai
    project_id = resolve_firestore_project_id()
    if project_id:
        vertexai.init(project=project_id, location=VERTEX_AI_LOCATION)
    else:
        vertexai.init(location=VERTEX_AI_LOCATION)


@lru_cache(maxsize=1)
def _embedding_model():
    from vertexai.language_models import TextEmbeddingModel
    _init_vertexai()
    return TextEmbeddingModel.from_pretrained("text-embedding-004")


def get_query_embedding(text: str, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
    """
    Converts text into a vector embedding using stable google-genai SDK profiles.
    Forces output truncation to 768 dimensions for database alignment.
    """
    from ..core.config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            # Upgraded call utilizing Matryoshka Representation to downscale dimensionality safely
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                    task_type=task_type
                )
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
        except Exception as e:
            print(f"⚡ Upgraded google-genai embedding execution failed: {e}")

    # Vertex AI Fallback path
    try:
        embeddings = _embedding_model().get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        print(f"Vertex AI embedding fallback failed: {e}")
        return [0.0] * 768


def _ordered_unique(values: list[Any]) -> list[Any]:
    seen = set()
    output = []
    for value in values:
        if value is None:
            continue
        key = (type(value), str(value).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").strip().lower().split())


def _grade_candidates(grade: object) -> list[Any]:
    raw = str(grade or "").strip()
    if not raw:
        return []
    digits = re.sub(r"\D+", "", raw)
    values: list[Any] = [raw]
    if digits:
        values.extend([f"Grade{digits}", f"grade_{digits}", digits, int(digits)])
    return _ordered_unique(values)


def _chapter_candidates(chapter: object) -> list[str]:
    raw = str(chapter or "").strip()
    if not raw:
        return []

    normalized = _normalize_text(raw)
    underscored = normalized.replace(" ", "_")
    values = [raw, normalized, underscored]

    match = re.search(r"\b(?:ch|chapter)\s*[_-]?\s*(\d{1,2})\b", normalized)
    if match:
        values.append(f"ch_{int(match.group(1)):02d}")

    mapped = GRADE_10_CHAPTER_IDS.get(normalized) or GRADE_10_CHAPTER_IDS.get(underscored)
    if mapped:
        values.append(mapped)

    return [str(value) for value in _ordered_unique(values)]


def _stream_nearest_in(
    query_vector: list[float],
    grades: list[Any] | None,
    chapters: list[str] | None,
    limit: int,
    metadata_filter: dict[str, Any] | None = None,
):
    firestore = _firestore_module()
    Vector = _vector_class()
    DistanceMeasure = _distance_measure_enum()
    metadata_filter = metadata_filter or {}

    query_ref = _collection_ref()
    if grades and "grade" not in metadata_filter:
        if len(grades) == 1:
            query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.grade", "==", grades[0]))
        else:
            query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.grade", "in", grades[:10]))
    
    if chapters and "chapter" not in metadata_filter:
        if len(chapters) == 1:
            query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.chapter", "==", chapters[0]))
        else:
            query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.chapter", "in", chapters[:10]))

    for key, value in metadata_filter.items():
        if value is None:
            continue
        query_ref = query_ref.where(filter=firestore.FieldFilter(f"metadata.{key}", "==", value))

    return query_ref.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_vector),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    ).stream(timeout=FIRESTORE_TIMEOUT_SECONDS)


def retrieve_context(
    query: str | None = None,
    grade: object = None,
    chapter: object | None = None,
    top_k: int = 4,
    *,
    k: int | None = None,
    topic: str | None = None,
    n_results: int | None = None,
    metadata_filter: dict[str, Any] | None = None,
    exam_type: str | None = None,
    phase: str | None = None,
    **_: Any,
) -> str:
    """Searches Firestore for the most relevant textbook chunks."""
    del exam_type

    try:
        query_text = str(query or topic or "").strip()
        if not query_text:
            return ""
        limit = max(1, int(k or n_results or top_k or 4))
        
        metadata_filter = metadata_filter or {}
        if phase:
            phase_l = str(phase).lower()
            if phase_l in {"teaching", "theory"}:
                metadata_filter["phase"] = "theory"
            elif phase_l in {"practice", "exercise", "exercises"}:
                metadata_filter["phase"] = "practice"
            elif phase_l in {"example", "examples"}:
                metadata_filter["phase"] = "examples"
            else:
                metadata_filter["phase"] = phase_l

        cache_key = (
            "rag_context|"
            f"{query_text}|{grade}|{chapter}|{limit}|"
            f"{metadata_filter or {}}"
        )
        cached = get_cache(cache_key)
        if isinstance(cached, str):
            return cached

        # Generate optimized lookup embeddings
        query_vector = get_query_embedding(query_text, task_type="RETRIEVAL_QUERY")

        grade_values = _grade_candidates(grade)
        chapter_values = _chapter_candidates(chapter)

        if sum(abs(v) for v in query_vector) < 1e-6:
            print("Warning: query_vector is zero. Falling back to non-vector Firebase metadata search.")
            firestore = _firestore_module()
            query_ref = _collection_ref()
            
            if chapter_values:
                query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.chapter", "in", chapter_values[:10]))
            elif grade_values:
                query_ref = query_ref.where(filter=firestore.FieldFilter("metadata.grade", "in", grade_values[:10]))
                
            for key, value in (metadata_filter or {}).items():
                if value is not None:
                    query_ref = query_ref.where(filter=firestore.FieldFilter(f"metadata.{key}", "==", value))

            context_chunks = []
            try:
                docs = query_ref.limit(limit * 2).stream(timeout=FIRESTORE_TIMEOUT_SECONDS)
                for doc in docs:
                    data = doc.to_dict()
                    text = str(data.get("text") or "").strip()
                    if text:
                        context_chunks.append(text)
            except Exception as e:
                print(f"Fallback metadata search failed: {e}")

            if not context_chunks:
                print(f"No chunks found for strict chapter {chapter_values}. Attempting broader fetch...")
                query_ref_broad = _collection_ref()
                for key, value in (metadata_filter or {}).items():
                    if value is not None:
                        query_ref_broad = query_ref_broad.where(filter=firestore.FieldFilter(f"metadata.{key}", "==", value))
                try:
                    docs = query_ref_broad.limit(limit * 4).stream(timeout=FIRESTORE_TIMEOUT_SECONDS)
                    for doc in docs:
                        data = doc.to_dict()
                        text = str(data.get("text") or "").strip()
                        meta_ch = str(data.get("metadata", {}).get("chapter", "")).lower()
                        if text and (not meta_ch or any(cv.lower() in meta_ch or cv.lower() in text.lower() for cv in chapter_values)):
                            context_chunks.append(text)
                except Exception:
                    pass

            if context_chunks:
                context = "\n\n---\n\n".join(context_chunks[:limit])
                set_cache(cache_key, context, ttl_seconds=RAG_CACHE_TTL_SECONDS)
                return context

            empty = "No specific curriculum context found for this topic."
            set_cache(cache_key, empty, ttl_seconds=RAG_CACHE_TTL_SECONDS)
            return empty
        
        search_scopes = []
        if grade_values and chapter_values:
            search_scopes.append((grade_values, chapter_values))
        elif grade_values:
            search_scopes.append((grade_values, None))
        elif chapter_values:
            search_scopes.append((None, chapter_values))
        else:
            search_scopes.append((None, None))
            
        if ALLOW_UNSCOPED_RAG_FALLBACK and (None, None) not in search_scopes:
            search_scopes.append((None, None))

        for batch_grades, batch_chapters in search_scopes:
            context_chunks = []
            docs = _stream_nearest_in(
                query_vector,
                batch_grades,
                batch_chapters,
                limit,
                metadata_filter=metadata_filter,
            )
            for doc in docs:
                data = doc.to_dict()
                text = str(data.get("text") or "").strip()
                if text:
                    context_chunks.append(text)
            if context_chunks:
                context = "\n\n---\n\n".join(context_chunks)
                set_cache(cache_key, context, ttl_seconds=RAG_CACHE_TTL_SECONDS)
                return context

        empty = "No specific curriculum context found for this topic."
        set_cache(cache_key, empty, ttl_seconds=RAG_CACHE_TTL_SECONDS)
        return empty

    except Exception as error:
        print(f"Error retrieving context from Firestore {RAG_COLLECTION}: {error}")
        return ""


def store_context_chunks(chunks: list[str], metadata: dict[str, Any], *, doc_prefix: str | None = None) -> int:
    """Store text chunks in Firestore vector storage for RAG retrieval."""
    clean_chunks = [str(chunk or "").strip() for chunk in chunks if str(chunk or "").strip()]
    if not clean_chunks:
        return 0

    Vector = _vector_class()
    db = _firestore_client()
    collection = db.collection(RAG_COLLECTION)
    prefix = doc_prefix or uuid.uuid4().hex
    stored = 0

    batch = db.batch()
    for index, chunk in enumerate(clean_chunks, start=1):
        # Generates document-optimized embedding vectors mapped exactly to 768 dimensions
        embedding = get_query_embedding(chunk, task_type="RETRIEVAL_DOCUMENT")
        doc_ref = collection.document(f"{prefix}_{index:04d}_{uuid.uuid4().hex[:8]}")
        batch.set(
            doc_ref,
            {
                "text": chunk,
                "embedding": Vector(embedding),
                "metadata": dict(metadata or {}),
            },
        )
        stored += 1
        if stored % 400 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()
    return stored


# --- BACKWARD COMPATIBILITY ALIASES ---
def embed_text(text: str) -> list[float]:
    """Exposes embedding generation for evaluation routes."""
    return get_query_embedding(text)


def get_context(query: str, grade: str, chapter: str, top_k: int = 4) -> str:
    """Exposes context retrieval for the proctor agent."""
    return retrieve_context(query, grade, chapter, top_k)