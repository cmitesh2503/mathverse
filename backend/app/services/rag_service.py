from pathlib import Path
import os
import re
from typing import Any

from ..core.config import GEMINI_API_KEY


retriever_instances: dict[str, object] = {}
vectorstores: dict[str, object] = {}
rag_disabled_reason: str | None = None
_embedding_instance: object | None = None
# Index path stays unchanged, but this FAISS index must be rebuilt with
# backend/create_index.py whenever EMBEDDING_MODEL changes.
FAISS_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "faiss_index"
CBSE_INDEX_NAME = "cbse_index"
JEE_INDEX_NAME = "jee_index"
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
PHASE_DOC_TYPE_FILTERS: dict[str, list[str]] = {
    "teaching": ["theory", "examples"],
    "practice": ["practice", "solutions"],
}
_CHAPTER_ALIAS_CACHE: dict[tuple[int | None, str, str], set[str]] = {}
CBSE_GRADE10_CHAPTER_ALIASES: dict[str, int] = {
    "real numbers": 1,
    "polynomials": 2,
    "pair of linear equations": 3,
    "pair of linear equations in two variables": 3,
    "quadratic equations": 4,
    "arithmetic progressions": 5,
    "triangles": 6,
    "coordinate geometry": 7,
    "introduction to trigonometry": 8,
    "some applications of trigonometry": 9,
    "applications of trigonometry": 9,
    "circles": 10,
    "constructions": 11,
    "areas related to circles": 12,
    "surface areas and volumes": 13,
    "statistics": 14,
    "probability": 15,
}


def _query_embeddings():
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    if EMBEDDING_MODEL.startswith("sentence-transformers/") or EMBEDDING_MODEL.startswith("all-"):
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings

        _embedding_instance = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        return _embedding_instance

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embedding_kwargs = {"model": EMBEDDING_MODEL, "task_type": "RETRIEVAL_QUERY"}
    if GEMINI_API_KEY:
        embedding_kwargs["google_api_key"] = GEMINI_API_KEY
    _embedding_instance = GoogleGenerativeAIEmbeddings(**embedding_kwargs)
    return _embedding_instance


def _normalize_exam_type(exam_type: str | None) -> str:
    return "jee" if (exam_type or "").lower() == "jee" else "cbse"


def _load_index(embeddings, index_name: str):
    from langchain_community.vectorstores import FAISS

    return FAISS.load_local(
        str(FAISS_INDEX_PATH),
        embeddings,
        index_name=index_name,
        allow_dangerous_deserialization=True,
    )


def _initialize_indexes() -> None:
    global rag_disabled_reason

    if vectorstores:
        return
    if rag_disabled_reason:
        raise RuntimeError(rag_disabled_reason)

    print("Initializing RAG indexes (only once)...")
    try:
        if not FAISS_INDEX_PATH.exists():
            raise FileNotFoundError(f"FAISS index directory not found: {FAISS_INDEX_PATH}")

        embeddings = _query_embeddings()

        try:
            vectorstores["cbse"] = _load_index(embeddings, CBSE_INDEX_NAME)
        except Exception:
            vectorstores["cbse"] = _load_index(embeddings, "index")

        try:
            vectorstores["jee"] = _load_index(embeddings, JEE_INDEX_NAME)
        except Exception:
            vectorstores["jee"] = vectorstores["cbse"]

        retriever_instances["cbse"] = vectorstores["cbse"].as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 15, "lambda_mult": 0.75},
        )
        retriever_instances["jee"] = vectorstores["jee"].as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 15, "lambda_mult": 0.75},
        )
        print(f"RAG loaded from {FAISS_INDEX_PATH}")
    except Exception as error:
        rag_disabled_reason = f"{type(error).__name__}: {error}"
        raise


def get_retriever(exam_type: str = "cbse"):
    _initialize_indexes()
    normalized_exam = _normalize_exam_type(exam_type)
    return retriever_instances.get(normalized_exam, retriever_instances["cbse"])


def _grade_number(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        pass

    match = re.search(r"\d+", str(value or ""))
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


def _doc_metadata_grade(doc: object) -> int | None:
    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    for key in ("grade", "class", "std"):
        grade = _grade_number(metadata.get(key))
        if grade is not None:
            return grade
    return None


def _normalize_match_value(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"(?i)\b(ch|chapter|grade|class|std)[\s_-]*(\d+)\b", r"\1 \2", text)
    text = text.replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def _chapter_number_aliases(index: int) -> set[str]:
    return {
        str(index),
        f"{index:02d}",
        f"ch {index}",
        f"ch {index:02d}",
        f"chapter {index}",
        f"chapter {index:02d}",
    }


def _chapter_aliases(chapter: str | None, grade: int | None, exam_type: str | None) -> set[str]:
    normalized_chapter = _normalize_match_value(chapter)
    if not normalized_chapter:
        return set()

    normalized_exam = _normalize_exam_type(exam_type)
    cache_key = (grade, normalized_exam, normalized_chapter)
    cached = _CHAPTER_ALIAS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    aliases = {normalized_chapter}
    if match := re.search(r"\d+", normalized_chapter):
        aliases.update(_chapter_number_aliases(int(match.group(0))))
    has_known_pdf_number = False
    if grade == 10 and normalized_exam == "cbse":
        chapter_number = CBSE_GRADE10_CHAPTER_ALIASES.get(normalized_chapter)
        if chapter_number is not None:
            has_known_pdf_number = True
            aliases.update(_chapter_number_aliases(chapter_number))

    if grade is not None and not has_known_pdf_number:
        try:
            from ..tutor_brain.curriculum import get_grade_curriculum

            curriculum = get_grade_curriculum(grade, normalized_exam)
            chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else []
        except Exception:
            chapters = []

        if isinstance(chapters, list):
            for index, item in enumerate(chapters, start=1):
                if not isinstance(item, dict):
                    continue
                candidate_values = [
                    item.get("slug"),
                    item.get("title"),
                    item.get("chapter"),
                    item.get("name"),
                ]
                normalized_candidates = {
                    _normalize_match_value(value)
                    for value in candidate_values
                    if str(value or "").strip()
                }
                if not normalized_candidates:
                    continue
                if any(
                    normalized_chapter == candidate
                    or normalized_chapter in candidate
                    or candidate in normalized_chapter
                    for candidate in normalized_candidates
                ):
                    aliases.update(normalized_candidates)
                    aliases.update(_chapter_number_aliases(index))

    _CHAPTER_ALIAS_CACHE[cache_key] = aliases
    return aliases


def _doc_matches_grade(doc: object, grade: int | None) -> bool:
    if grade is None:
        return True
    doc_grade = _doc_metadata_grade(doc)
    return doc_grade is None or doc_grade == grade


def _doc_matches_phase(doc: object, phase: str | None) -> bool:
    normalized_phase = str(phase or "").strip().lower()
    if not normalized_phase:
        return True
    allowed_doc_types = PHASE_DOC_TYPE_FILTERS.get(normalized_phase)
    if not allowed_doc_types:
        return True

    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return False
    value = metadata.get("doc_type")
    if isinstance(value, str):
        return value.strip().lower() in set(allowed_doc_types)
    if isinstance(value, (list, tuple, set)):
        normalized = {str(item).strip().lower() for item in value}
        return bool(normalized.intersection(allowed_doc_types))
    return False


def _doc_matches_chapter(
    doc: object,
    chapter: str | None,
    *,
    grade: int | None = None,
    exam_type: str | None = None,
) -> bool:
    aliases = _chapter_aliases(chapter, grade, exam_type)
    if not aliases:
        return True

    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return False

    candidates = [
        metadata.get("chapter"),
        metadata.get("chapter_name"),
        metadata.get("chapter_title"),
        metadata.get("source_file"),
        metadata.get("source_path"),
    ]
    normalized_candidates = {
        _normalize_match_value(candidate)
        for candidate in candidates
        if str(candidate or "").strip()
    }
    if not normalized_candidates:
        return False
    return bool(aliases.intersection(normalized_candidates))


def embed_text(text: str) -> list[float]:
    embeddings = _query_embeddings()
    content = str(text or "")
    if hasattr(embeddings, "embed_query"):
        return list(embeddings.embed_query(content))
    if hasattr(embeddings, "embed_documents"):
        return list(embeddings.embed_documents([content])[0])
    raise RuntimeError("Embedding backend does not support embed_query/embed_documents.")


def get_context(
    query: str,
    exam_type: str = "cbse",
    k: int = 3,
    grade: int | None = None,
    chapter: str | None = None,
    phase: str | None = None,
) -> str:
    _initialize_indexes()
    normalized_exam = _normalize_exam_type(exam_type)
    store = vectorstores.get(normalized_exam, vectorstores.get("cbse"))
    if store is None:
        return ""

    target_k = max(2, int(k or 3))
    normalized_phase = str(phase or "").strip().lower()
    filtered_doc_types = PHASE_DOC_TYPE_FILTERS.get(normalized_phase, [])
    metadata_filter: dict[str, object] = {}
    normalized_grade = _grade_number(grade)
    print(
        "Searching RAG: "
        f"Grade: {normalized_grade or grade} | Chapter: {chapter} | "
        f"Phase: {phase} | Filtered Doc Types: {filtered_doc_types}"
    )

    docs = []
    try:
        retriever_kwargs: dict[str, object] = {
            "k": target_k,
            "fetch_k": max(10, target_k * 3),
            "lambda_mult": 0.75,
        }
        if metadata_filter:
            retriever_kwargs["filter"] = metadata_filter
        docs = store.as_retriever(
            search_type="mmr",
            search_kwargs=retriever_kwargs,
        ).invoke(query)
    except Exception:
        retriever = get_retriever(exam_type=normalized_exam)
        docs = retriever.invoke(query)

    if normalized_grade is not None:
        filtered = [doc for doc in docs if _doc_matches_grade(doc, normalized_grade)]
        if filtered:
            docs = filtered
    if chapter is not None:
        filtered = [
            doc
            for doc in docs
            if _doc_matches_chapter(
                doc,
                chapter,
                grade=normalized_grade,
                exam_type=normalized_exam,
            )
        ]
        if filtered:
            docs = filtered
    if phase is not None:
        filtered = [doc for doc in docs if _doc_matches_phase(doc, phase)]
        if filtered:
            docs = filtered

    return "\n\n".join(
        (doc.page_content or "").strip()
        for doc in docs[:target_k]
        if getattr(doc, "page_content", None)
    )


def _metadata_grade(metadata_filter: dict[str, Any]) -> int | None:
    return _grade_number(metadata_filter.get("grade"))


def _retrieve_chroma_context(query: str, n_results: int, metadata_filter: dict[str, Any] | None) -> str:
    try:
        import chromadb

        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(name="cbse_curriculum")
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [embed_text(query)],
            "n_results": max(1, int(n_results or 5)),
        }
        if metadata_filter:
            query_kwargs["where"] = metadata_filter
        results = collection.query(**query_kwargs)
        documents = results.get("documents") or []
        if not documents:
            return ""
        rows = documents[0] if isinstance(documents[0], list) else documents
        return "\n\n".join(str(item).strip() for item in rows if str(item).strip())
    except Exception as error:
        print(f"Chroma retrieval unavailable ({type(error).__name__}): {error}")
        return ""


def retrieve_context(
    query: str | None = None,
    exam_type: str = "cbse",
    k: int = 8,
    grade: int | None = None,
    chapter: str | None = None,
    phase: str | None = None,
    *,
    topic: str | None = None,
    n_results: int | None = None,
    metadata_filter: dict[str, Any] | None = None,
) -> str:
    resolved_query = str(query or topic or "").strip()
    if not resolved_query:
        return ""

    resolved_k = int(n_results) if n_results is not None else int(k or 8)
    resolved_k = max(1, resolved_k)

    resolved_grade = grade
    resolved_chapter = chapter
    if isinstance(metadata_filter, dict):
        if resolved_grade is None:
            resolved_grade = _metadata_grade(metadata_filter)
        if resolved_chapter is None and metadata_filter.get("chapter") is not None:
            resolved_chapter = str(metadata_filter.get("chapter") or "").strip() or None

        # Backward-compatible path for evaluation test materials indexed in Chroma.
        unsupported_keys = set(metadata_filter) - {"grade", "chapter", "doc_type"}
        if unsupported_keys:
            chroma_context = _retrieve_chroma_context(resolved_query, resolved_k, metadata_filter)
            if chroma_context:
                return chroma_context

    try:
        return get_context(
            query=resolved_query,
            exam_type=exam_type,
            k=resolved_k,
            grade=resolved_grade,
            chapter=resolved_chapter,
            phase=phase,
        )
    except Exception as error:
        # Fail open so tutoring can continue even when local embedding/index deps are unavailable.
        if not rag_disabled_reason:
            print(f"RAG context unavailable ({type(error).__name__}): {error}")
        return ""
