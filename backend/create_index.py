import os
import glob
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
#from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
import pickle

# Configuration
CURRICULUM_ROOT = "app/data/curriculum/cbse"
INDEX_SAVE_PATH = "data/faiss_index"

def create_index():
    print(f"🚀 Starting Indexing from: {CURRICULUM_ROOT}")
    
    # Ensure index directory exists
    os.makedirs(INDEX_SAVE_PATH, exist_ok=True)
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    all_docs = []
    
    # 1. Recursive Crawl
    pdf_files = list(Path(CURRICULUM_ROOT).rglob("*.pdf"))
    
    for pdf_path in pdf_files:
        # Extract metadata from path: .../grade_10/ch_01/theory.pdf
        # pdf_path.parts gives ('app', 'data', 'curriculum', 'cbse', 'grade_10', 'ch_01', 'theory.pdf')
        parts = pdf_path.parts
        grade = parts[-3]
        chapter = parts[-2]
        doc_type = pdf_path.stem # e.g., 'theory'
        
        print(f"✅ Indexing: {grade} | {chapter} | {doc_type}")
        
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        
        # Inject Metadata
        for doc in docs:
            doc.metadata.update({
                "grade": grade,
                "chapter": chapter,
                "doc_type": doc_type
            })
            
        chunks = splitter.split_documents(docs)
        all_docs.extend(chunks)
        
    # 2. Build Index
    print(f"🧠 Building FAISS index with {len(all_docs)} chunks...")
    print("🧠 Initializing local embeddings (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(all_docs, embeddings)
    
    # 3. Save
    vectorstore.save_local(INDEX_SAVE_PATH)
    print(f"🎉 Index saved to {INDEX_SAVE_PATH}")

if __name__ == "__main__":
    create_index()