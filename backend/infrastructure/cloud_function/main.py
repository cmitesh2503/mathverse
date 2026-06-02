import os
import fitz  # PyMuPDF
import functions_framework
from google.cloud import storage
from google.cloud import firestore
from vertexai.language_models import TextEmbeddingModel
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize GCP Clients globally for "Cold Start" optimization
PROJECT_ID = os.environ.get("PROJECT_ID")
FIRESTORE_COL = os.environ.get("FIRESTORE_COL", "curriculum_chunks")
EMBEDDING_MODEL_NAME = "text-embedding-004"

storage_client = storage.Client(project=PROJECT_ID)
db = firestore.Client(project=PROJECT_ID)

def get_embedding(text: str) -> list[float]:
    """Calls Gemini Vertex AI to get the vector embedding for a text chunk."""
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
    embeddings = model.get_embeddings([text])
    return embeddings[0].values

def parse_metadata_from_path(file_path: str):
    """
    Extracts metadata from your folder structure.
    Expects format: Grade10/ch_06_triangles/theory.pdf
    """
    parts = file_path.split('/')
    grade = parts[0] if len(parts) > 0 else "UnknownGrade"
    
    # Extract just 'ch_06' from 'ch_06_triangles' to match frontend requests
    raw_chapter = parts[1] if len(parts) > 1 else "UnknownChapter"
    if raw_chapter.startswith("ch_"):
        chapter = "_".join(raw_chapter.split('_')[:2]) 
    elif raw_chapter.lower().startswith("chapter"):
        chapter = raw_chapter
    else:
        chapter = raw_chapter
        
    doc_type = parts[-1].replace('.pdf', '') if len(parts) > 2 else "UnknownType"
    
    return grade, chapter, doc_type

@functions_framework.cloud_event
def process_new_pdf(cloud_event):
    """Triggered automatically by a new file drop in Cloud Storage."""
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    if not file_name.endswith('.pdf'):
        print(f"Skipping non-PDF file: {file_name}")
        return

    print(f"🚀 Waking up! Processing new curriculum file: {file_name}")
    grade, chapter, doc_type = parse_metadata_from_path(file_name)

    # 1. Download PDF to temporary cloud memory
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    tmp_path = f"/tmp/{file_name.replace('/', '_')}"
    blob.download_to_filename(tmp_path)

    # 2. Extract Text cleanly using PyMuPDF
    text_content = ""
    with fitz.open(tmp_path) as doc:
        for page in doc:
            text_content += page.get_text("text") + "\n"

    # 3. Chunk Text for the AI
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text_content)
    print(f"📚 Extracted {len(chunks)} text chunks from {file_name}")

    # 4. Embed and Save directly to Firestore DB
    batch = db.batch()
    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        
        doc_ref = db.collection(FIRESTORE_COL).document(f"{grade}_{chapter}_{doc_type}_chunk_{i}")
        
        batch.set(doc_ref, {
            "text": chunk,
            "embedding": vector,  # Native vector storage
            "metadata": {
                "grade": grade,
                "chapter": chapter,
                "doc_type": doc_type,
                "source": file_name
            }
        })
        
        # Firestore batches max out at 500 ops. Commit safely at 400.
        if (i + 1) % 400 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()
    os.remove(tmp_path) 
    print(f"✅ Success! Indexed {file_name} into Firebase.")