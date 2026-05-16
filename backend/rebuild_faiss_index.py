from __future__ import annotations

import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


PROJECT_ROOT = Path(__file__).resolve().parent
PDF_ROOT = PROJECT_ROOT / "app" / "data" / "pdfs"
INDEX_DIR = PROJECT_ROOT / "data" / "faiss_index"
CBSE_INDEX_NAME = "cbse_index"


def _embedding_model():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _grade_from_path(path: Path) -> int | None:
    match = re.search(r"std[_\s-]*(\d+)", str(path.parent).lower())
    if match:
        return int(match.group(1))

    name = path.name.lower().replace(" ", "")
    match = re.search(r"class(\d+)", name)
    if match:
        return int(match.group(1))
    return None


def _chapter_from_name(path: Path) -> int | None:
    name = path.name.lower().replace(" ", "")
    for pattern in (r"ch[-_]?(\d+)", r"chapter[-_]?(\d+)"):
        match = re.search(pattern, name)
        if match:
            return int(match.group(1))
    return None


def _load_documents() -> list[Document]:
    if not PDF_ROOT.exists():
        raise FileNotFoundError(f"PDF directory not found: {PDF_ROOT}")

    all_docs: list[Document] = []
    pdf_files = [
        path
        for path in sorted(PDF_ROOT.rglob("*.pdf"))
        if "jee_main" not in str(path).lower().replace("\\", "/")
    ]
    print(f"Found {len(pdf_files)} PDF files under {PDF_ROOT}")

    for pdf_path in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
            grade = _grade_from_path(pdf_path)
            chapter = _chapter_from_name(pdf_path)
            for doc in docs:
                md = dict(doc.metadata or {})
                md["source_file"] = pdf_path.name
                md["source_path"] = str(pdf_path.relative_to(PDF_ROOT))
                md["grade"] = grade
                md["chapter"] = chapter
                md["board"] = "cbse"
                md["subject"] = "mathematics"
                doc.metadata = md
            all_docs.extend(docs)
            print(f"Loaded {len(docs):4d} pages from {pdf_path.relative_to(PDF_ROOT)}")
        except Exception as error:
            print(f"Failed to load {pdf_path}: {error}")

    if not all_docs:
        raise RuntimeError("No PDF pages loaded. Cannot build FAISS index.")
    return all_docs


def rebuild_index() -> None:
    docs = _load_documents()
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=140)
    raw_chunks = splitter.split_documents(docs)
    chunks: list[Document] = []
    for chunk in raw_chunks:
        text = chunk.page_content
        if text is None:
            continue
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            continue
        chunk.page_content = text
        chunks.append(chunk)

    print(f"Total chunks: {len(chunks)}")
    if not chunks:
        raise RuntimeError("No valid text chunks after cleaning.")

    embeddings = _embedding_model()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR), index_name=CBSE_INDEX_NAME)
    # Backward-compatible default index alias.
    vectorstore.save_local(str(INDEX_DIR), index_name="index")
    print(f"Saved FAISS indexes to {INDEX_DIR} as '{CBSE_INDEX_NAME}' and 'index'")


if __name__ == "__main__":
    rebuild_index()
