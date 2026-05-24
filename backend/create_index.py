from pathlib import Path
import os
import random
import re
import shutil
import time

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

INDEX_DIR = Path(__file__).resolve().parent / "data" / "faiss_index"
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
CURRICULUM_ROOT = BACKEND_DIR / "data" / "curriculum" / os.getenv("RAG_CURRICULUM_GRADE", "Grade10")

# We keep a strict two-phase tag for downstream gating.
# solution.pdf is indexed under practice so retrieval can filter by theory vs practice.
PDF_TYPE_MAP = {
    "theory": "theory",
    "practice": "practice",
    "solution": "practice",
}

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY in backend/.env "
        "or your shell environment before running create_index.py."
    )

EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "gemini-embedding-2-preview")
EMBED_BATCH_SIZE = max(1, int(os.getenv("RAG_EMBED_BATCH_SIZE", "96")))
EMBED_BATCH_PAUSE_SECONDS = max(0.0, float(os.getenv("RAG_EMBED_BATCH_PAUSE_SECONDS", "0.7")))
EMBED_MAX_RETRIES = max(1, int(os.getenv("RAG_EMBED_MAX_RETRIES", "12")))
EMBED_DEFAULT_RETRY_SECONDS = max(5.0, float(os.getenv("RAG_EMBED_DEFAULT_RETRY_SECONDS", "30")))
EMBED_MAX_BACKOFF_SECONDS = max(10.0, float(os.getenv("RAG_EMBED_MAX_BACKOFF_SECONDS", "120")))


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "resource_exhausted" in message
        or "quota exceeded" in message
        or "429" in message
        or "retry in" in message
    )


def _is_transient_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "503" in message
        or "unavailable" in message
        or "deadline_exceeded" in message
        or "timeout" in message
        or "temporarily unavailable" in message
        or "connection reset" in message
        or "connection aborted" in message
        or "connection error" in message
        or "internal" in message
        or "500" in message
    )


def _extract_retry_seconds(error: Exception) -> float:
    message = str(error)
    patterns = (
        r"retry in\s*([0-9]+(?:\.[0-9]+)?)s",
        r"retrydelay['\"]?:\s*['\"]?([0-9]+(?:\.[0-9]+)?)s",
    )
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                return max(1.0, float(match.group(1)) + 1.0)
            except ValueError:
                continue
    return EMBED_DEFAULT_RETRY_SECONDS


def _retry_wait_seconds(error: Exception, attempt: int) -> float:
    if _is_quota_error(error):
        return _extract_retry_seconds(error)
    base = min(EMBED_MAX_BACKOFF_SECONDS, EMBED_DEFAULT_RETRY_SECONDS * (2 ** max(0, attempt - 1)))
    # Jitter avoids synchronized retry bursts against the API.
    return min(EMBED_MAX_BACKOFF_SECONDS, base + random.uniform(0.0, 2.5))


def _infer_doc_type(pdf_path: Path) -> str | None:
    return PDF_TYPE_MAP.get(pdf_path.stem.strip().lower())


def load_documents(root: Path = CURRICULUM_ROOT) -> list:
    if not root.exists():
        raise FileNotFoundError(f"Curriculum root not found: {root}")

    documents = []
    pdf_paths = sorted(root.rglob("*.pdf"))
    for pdf_path in pdf_paths:
        chapter_dir = next((parent for parent in pdf_path.parents if parent.name.lower().startswith("chapter")), None)
        if chapter_dir is None:
            print(f"Skipping PDF outside chapter folder: {pdf_path}")
            continue

        chapter_name = chapter_dir.name
        doc_type = _infer_doc_type(pdf_path)
        if not doc_type:
            print(f"Skipping unsupported PDF in {chapter_name}: {pdf_path.name}")
            continue

        try:
            page_docs = PyPDFLoader(str(pdf_path)).load()
        except Exception as error:
            print(f"Failed to load {pdf_path}: {error}")
            continue

        for doc in page_docs:
            metadata = dict(getattr(doc, "metadata", {}) or {})
            metadata.update(
                {
                    "chapter": chapter_name,
                    "type": doc_type,
                    "source_file": pdf_path.name,
                    "source_path": str(pdf_path.relative_to(BACKEND_DIR)),
                }
            )
            doc.metadata = metadata
            documents.append(doc)

        print(f"Loaded {chapter_name}/{pdf_path.name} ({len(page_docs)} pages, type={doc_type})")

    if not documents:
        raise RuntimeError(f"No supported curriculum documents found under: {root}")
    return documents


def _build_vectorstore_in_batches(chunks: list, embeddings) -> FAISS:
    total = len(chunks)
    if total == 0:
        raise RuntimeError("No chunks available for indexing.")

    total_batches = (total + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    vectorstore: FAISS | None = None

    for batch_index, start in enumerate(range(0, total, EMBED_BATCH_SIZE), start=1):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        attempt = 0

        while True:
            attempt += 1
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(batch, embeddings)
                else:
                    vectorstore.add_documents(batch)
                break
            except Exception as error:
                retryable = _is_quota_error(error) or _is_transient_error(error)
                if retryable and attempt <= EMBED_MAX_RETRIES:
                    wait_seconds = _retry_wait_seconds(error, attempt)
                    reason = "quota/rate-limit" if _is_quota_error(error) else "temporary service/network error"
                    print(
                        f"Retryable {reason} on batch {batch_index}/{total_batches}. "
                        f"Retry {attempt}/{EMBED_MAX_RETRIES} in {wait_seconds:.1f}s..."
                    )
                    time.sleep(wait_seconds)
                    continue
                raise

        processed = min(start + len(batch), total)
        print(f"Indexed chunks: {processed}/{total}")
        if processed < total and EMBED_BATCH_PAUSE_SECONDS > 0:
            time.sleep(EMBED_BATCH_PAUSE_SECONDS)

    if vectorstore is None:
        raise RuntimeError("Failed to create FAISS vectorstore.")
    return vectorstore

print(f"Loading curriculum documents from: {CURRICULUM_ROOT}")
documents = load_documents()
print(f"Total documents loaded: {len(documents)}")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
)

chunks = splitter.split_documents(documents)

# Ensure saved FAISS docstore entries always carry phase-gating metadata.
for chunk in chunks:
    metadata = dict(getattr(chunk, "metadata", {}) or {})
    chapter = str(metadata.get("chapter") or "").strip()
    doc_type = str(metadata.get("type") or "").strip().lower()
    if not chapter:
        chapter = "UnknownChapter"
    if doc_type not in {"theory", "practice"}:
        doc_type = "practice"
    metadata["chapter"] = chapter
    metadata["type"] = doc_type
    chunk.metadata = metadata

print(f"Total chunks: {len(chunks)}")

embedding_kwargs = {
    "model": EMBEDDING_MODEL,
    "task_type": "RETRIEVAL_DOCUMENT",
    "google_api_key": GOOGLE_API_KEY,
}

embeddings = GoogleGenerativeAIEmbeddings(**embedding_kwargs)

print(f"Creating FAISS index with {EMBEDDING_MODEL}...")
vectorstore = _build_vectorstore_in_batches(chunks, embeddings)

if INDEX_DIR.exists():
    shutil.rmtree(INDEX_DIR)

vectorstore.save_local(str(INDEX_DIR))

print(f"Index created successfully at {INDEX_DIR}")
