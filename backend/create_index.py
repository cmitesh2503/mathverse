from app.tutor_brain.tutor_engine import load_ncert_content
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

print("📚 Loading documents...")
documents = load_ncert_content()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = splitter.split_documents(documents)

print(f"📄 Total chunks: {len(chunks)}")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

print("🔄 Creating FAISS index...")
vectorstore = FAISS.from_documents(chunks, embeddings)

vectorstore.save_local("backend/data/faiss_index")

print("✅ Index created successfully!")