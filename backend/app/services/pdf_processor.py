import PyPDF2
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from ..core.config import GEMINI_API_KEY
import chromadb
from chromadb.config import Settings

client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def chunk_text(text, grade, subject="Math"):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)
    chunk_data = [{"text": chunk, "grade": grade, "subject": subject, "topic": f"grade_{grade}_topic"} for chunk in chunks]
    return chunk_data

def embed_text(text):
    result = genai.embed_content(
        model="models/embedding-001",
        content=text
    )
    return result['embedding']

def store_chunks(chunks):
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="cbse_curriculum")

    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk["text"])
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            metadatas=[{"grade": chunk["grade"], "subject": chunk["subject"], "topic": chunk["topic"]}],
            documents=[chunk["text"]]
        )

def process_pdf(pdf_path, grade):
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text, grade)
    store_chunks(chunks)
    print(f"Processed {len(chunks)} chunks for grade {grade}")

# Example usage
# process_pdf("path/to/cbse_math_grade_10.pdf", 10)