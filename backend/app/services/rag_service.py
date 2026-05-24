from pathlib import Path
import os

from ..core.config import GEMINI_API_KEY


retriever_instances: dict[str, object] = {}
vectorstores: dict[str, object] = {}
rag_disabled_reason: str | None = None
# Index path stays unchanged, but this FAISS index must be rebuilt with
# backend/create_index.py whenever EMBEDDING_MODEL changes.
FAISS_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "faiss_index"
CBSE_INDEX_NAME = "cbse_index"
JEE_INDEX_NAME = "jee_index"
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "gemini-embedding-2-preview")


def _query_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embedding_kwargs = {
        "model": EMBEDDING_MODEL,
        "task_type": "RETRIEVAL_QUERY",
    }
    if GEMINI_API_KEY:
        embedding_kwargs["google_api_key"] = GEMINI_API_KEY
    return GoogleGenerativeAIEmbeddings(**embedding_kwargs)


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


def _doc_metadata_grade(doc: object) -> int | None:
    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    for key in ("grade", "class", "std"):
        raw = metadata.get(key)
        try:
            if raw is not None:
                return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _doc_matches_phase(doc: object, phase: str | None) -> bool:
    normalized_phase = str(phase or "").strip().lower()
    if not normalized_phase:
        return True
    if normalized_phase != "teaching":
        return True

    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return False

    def contains_theory(value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() == "theory"
        if isinstance(value, (list, tuple, set)):
            return any(contains_theory(item) for item in value)
        return False

    for key in ("phase", "content_type", "chunk_type", "type", "tag", "tags", "category", "section"):
        if contains_theory(metadata.get(key)):
            return True
    return False


def get_context(
    query: str,
    exam_type: str = "cbse",
    k: int = 3,
    grade: int | None = None,
    phase: str | None = None,
) -> str:
    _initialize_indexes()
    normalized_exam = _normalize_exam_type(exam_type)
    store = vectorstores.get(normalized_exam, vectorstores.get("cbse"))
    if store is None:
        return ""

    target_k = max(2, int(k or 3))
    docs = []
    try:
        docs = store.max_marginal_relevance_search(query, k=target_k, fetch_k=max(10, target_k * 3))
    except Exception:
        retriever = get_retriever(exam_type=normalized_exam)
        docs = retriever.invoke(query)

    if grade is not None:
        filtered = [doc for doc in docs if _doc_metadata_grade(doc) in {None, int(grade)}]
        if filtered:
            docs = filtered
    if phase is not None:
        docs = [doc for doc in docs if _doc_matches_phase(doc, phase)]

    return "\n\n".join(
        (doc.page_content or "").strip()
        for doc in docs[:target_k]
        if getattr(doc, "page_content", None)
    )


def retrieve_context(
    query: str,
    exam_type: str = "cbse",
    k: int = 8,
    grade: int | None = None,
    phase: str | None = None,
) -> str:
    try:
        return get_context(query=query, exam_type=exam_type, k=k, grade=grade, phase=phase)
    except Exception as error:
        # Fail open so tutoring can continue even when local embedding/index deps are unavailable.
        if not rag_disabled_reason:
            print(f"RAG context unavailable ({type(error).__name__}): {error}")
        return ""
