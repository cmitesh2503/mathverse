from pathlib import Path
import warnings


retriever_instances: dict[str, object] = {}
vectorstores: dict[str, object] = {}
rag_disabled_reason: str | None = None
FAISS_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "faiss_index"
CBSE_INDEX_NAME = "cbse_index"
JEE_INDEX_NAME = "jee_index"


def _embedding_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings
    except ImportError:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"The class `HuggingFaceEmbeddings` was deprecated in LangChain")
            from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings


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

        embeddings_cls = _embedding_class()
        embeddings = embeddings_cls(model_name="sentence-transformers/all-MiniLM-L6-v2")

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
            search_kwargs={"k": 10, "fetch_k": 40, "lambda_mult": 0.65},
        )
        retriever_instances["jee"] = vectorstores["jee"].as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "fetch_k": 40, "lambda_mult": 0.65},
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


def get_context(query: str, exam_type: str = "cbse", k: int = 8, grade: int | None = None) -> str:
    _initialize_indexes()
    normalized_exam = _normalize_exam_type(exam_type)
    store = vectorstores.get(normalized_exam, vectorstores.get("cbse"))
    if store is None:
        return ""

    target_k = max(6, int(k or 8))
    docs = []
    try:
        docs = store.max_marginal_relevance_search(query, k=target_k, fetch_k=max(24, target_k * 4))
    except Exception:
        retriever = get_retriever(exam_type=normalized_exam)
        docs = retriever.invoke(query)

    if grade is not None:
        filtered = [doc for doc in docs if _doc_metadata_grade(doc) in {None, int(grade)}]
        if filtered:
            docs = filtered

    return "\n\n".join(
        (doc.page_content or "").strip()
        for doc in docs[:target_k]
        if getattr(doc, "page_content", None)
    )


def retrieve_context(query: str, exam_type: str = "cbse", k: int = 8, grade: int | None = None) -> str:
    try:
        return get_context(query=query, exam_type=exam_type, k=k, grade=grade)
    except Exception as error:
        # Fail open so tutoring can continue even when local embedding/index deps are unavailable.
        if not rag_disabled_reason:
            print(f"RAG context unavailable ({type(error).__name__}): {error}")
        return ""
