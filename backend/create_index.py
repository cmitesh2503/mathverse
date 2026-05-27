from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter


BACKEND_DIR = Path(__file__).resolve().parent
CURRICULUM_ROOT = BACKEND_DIR / "data" / "curriculum"
LEGACY_PDF_ROOT = BACKEND_DIR / "app" / "data" / "pdfs"
INDEX_SAVE_PATH = BACKEND_DIR / "data" / "faiss_index"


def _embedding_model():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def load_documents():
    all_docs = []
    pdf_roots = [root for root in (CURRICULUM_ROOT, LEGACY_PDF_ROOT) if root.exists()]
    if not pdf_roots:
        raise FileNotFoundError(
            f"No PDF roots found. Checked: {CURRICULUM_ROOT}, {LEGACY_PDF_ROOT}"
        )

    pdf_files = []
    for root in pdf_roots:
        root_files = sorted(root.rglob("*.pdf"))
        print(f"Found {len(root_files)} PDF files under {root}")
        pdf_files.extend((root, path) for path in root_files)

    for root, pdf_path in pdf_files:
        chapter_dir = next(
            (
                parent
                for parent in pdf_path.parents
                if parent.name.lower().startswith("chapter")
                or parent.name.lower().startswith("ch_")
            ),
            None,
        )
        if chapter_dir is not None:
            grade_dir = chapter_dir.parent
            grade_name = grade_dir.name
            chapter_name = chapter_dir.name
            doc_type = pdf_path.stem
        else:
            grade_dir = pdf_path.parent
            grade_name = grade_dir.name
            chapter_name = pdf_path.stem
            doc_type = "theory"

        print(f"Indexing: {grade_name} | {chapter_name} | {doc_type}")

        try:
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
        except Exception as error:
            print(f"Failed to load {pdf_path}: {error}")
            continue

        for doc in docs:
            metadata = dict(doc.metadata or {})
            metadata.update(
                {
                    "grade": grade_name,
                    "chapter": chapter_name,
                    "doc_type": doc_type,
                    "source_file": pdf_path.name,
                    "source_path": str(pdf_path.relative_to(root)),
                }
            )
            doc.metadata = metadata

        all_docs.extend(docs)

    if not all_docs:
        raise RuntimeError("No PDF pages loaded. Cannot build FAISS index.")
    return all_docs


def create_index():
    print(f"Starting indexing from: {CURRICULUM_ROOT}")
    INDEX_SAVE_PATH.mkdir(parents=True, exist_ok=True)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = load_documents()
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        metadata = dict(chunk.metadata or {})
        metadata["grade"] = metadata.get("grade") or "UnknownGrade"
        chunk.metadata = metadata

    print(f"Building FAISS index with {len(chunks)} chunks...")
    print("Initializing local embeddings (all-MiniLM-L6-v2)...")
    embeddings = _embedding_model()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    for doc in vectorstore.docstore._dict.values():
        metadata = dict(doc.metadata or {})
        grade = metadata.get("grade") or "UnknownGrade"
        metadata["grade"] = grade
        doc.metadata = metadata

    vectorstore.save_local(str(INDEX_SAVE_PATH))
    print(f"Index saved to {INDEX_SAVE_PATH}")


if __name__ == "__main__":
    create_index()
