from pathlib import Path
import warnings


retriever_instance = None
FAISS_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "faiss_index"


def _embedding_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings
    except ImportError:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"The class `HuggingFaceEmbeddings` was deprecated in LangChain")
            from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings


def get_retriever():
    global retriever_instance

    if retriever_instance is None:
        print("Initializing RAG (only once)...")
        from langchain_community.vectorstores import FAISS

        if not FAISS_INDEX_PATH.exists():
            raise FileNotFoundError(f"FAISS index not found: {FAISS_INDEX_PATH}")

        embeddings_cls = _embedding_class()
        embeddings = embeddings_cls(model_name="sentence-transformers/all-MiniLM-L6-v2")
        db = FAISS.load_local(
            str(FAISS_INDEX_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        retriever_instance = db.as_retriever(search_kwargs={"k": 3})
        print(f"RAG loaded from {FAISS_INDEX_PATH}")

    return retriever_instance
