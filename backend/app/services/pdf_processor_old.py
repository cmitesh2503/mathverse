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

def chunk_text(text, grade, subject="Math", topic=None, source=None):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)
    topic_name = topic or f"grade_{grade}_topic"
    chunk_data = [
        {
            "text": chunk,
            "grade": grade,
            "subject": subject,
            "topic": topic_name,
            "source": source or "ncert_pdf",
        }
        for chunk in chunks
    ]
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
            ids=[f"chunk_{chunk['grade']}_{chunk['topic']}_{i}"],
            embeddings=[embedding],
            metadatas=[{
                "grade": chunk["grade"],
                "subject": chunk["subject"],
                "topic": chunk["topic"],
                "source": chunk.get("source", "ncert_pdf"),
            }],
            documents=[chunk["text"]]
        )

def process_pdf(pdf_path, grade, topic=None, subject="Math", source=None):
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text, grade, subject=subject, topic=topic, source=source)
    store_chunks(chunks)
    print(f"Processed {len(chunks)} chunks for grade {grade}, topic={topic}")

# Example usage
# process_pdf("path/to/cbse_math_grade_10.pdf", 10, topic="pair_of_linear_equations_in_two_variables", source="NCERT_Mathematics_Grade_10")