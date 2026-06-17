import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from google.cloud import storage
from pypdf import PdfReader

# Import the RAG storage utility updated earlier
from app.services.rag_service import store_context_chunks


def parse_metadata_from_path(blob_name: str) -> Tuple[str, str, str, str]:
    """
    Parses GCS folder path dynamically to extract RAG metadata.
    Supports common educational directory structures such as:
      - boards/CBSE/grade_10/circles/theory.pdf
      - grade_10/real_numbers/practice.pdf
      - CBSE/grade_10/triangles/theory.pdf
      
    Returns:
        Tuple[grade, chapter_slug, phase, school_board]
    """
    normalized_path = blob_name.replace("\\", "/").strip("/")
    path_parts = normalized_path.split("/")
    
    # Set safe default fallbacks
    grade = "10"
    chapter_slug = "general"
    phase = "theory"
    school_board = "CBSE"
    
    # 1. Parse Board (e.g., CBSE, ICSE, STATE)
    for part in path_parts:
        if part.upper() in ["CBSE", "ICSE", "STATE", "IB"]:
            school_board = part.upper()
            break
            
    # 2. Parse Grade (looks for 'grade_10', 'grade10', 'class_10', 'g10')
    for part in path_parts:
        grade_match = re.search(r"(?:grade|class|g)[_-]?(\d+)", part, re.IGNORECASE)
        if grade_match:
            grade = grade_match.group(1)
            break
            
    # 3. Parse Phase (looks for 'theory', 'practice', 'exercise', 'examples')
    filename = path_parts[-1].lower()
    if "practice" in filename or "exercise" in filename or "test" in filename:
        phase = "practice"
    elif "example" in filename:
        phase = "examples"
    else:
        # Check subfolders for phase clues if not in filename
        for part in path_parts[:-1]:
            part_lower = part.lower()
            if part_lower in ["theory", "practice", "examples"]:
                phase = part_lower
                break

    # 4. Parse Chapter Slug
    # Usually, the folder immediately preceding the filename (or the phase folder) represents the chapter
    if len(path_parts) >= 2:
        candidate_slug = path_parts[-2].lower()
        # If the direct parent folder is a known phase, go one level up
        if candidate_slug in ["theory", "practice", "examples", "lecture"] and len(path_parts) >= 3:
            candidate_slug = path_parts[-3].lower()
            
        # Clean the slug format
        clean_slug = re.sub(r"[^\w\s-]", "", candidate_slug).strip().replace(" ", "_")
        if clean_slug:
            chapter_slug = clean_slug

    print(f"🕵️  Dynamic Path Parser Results for '{blob_name}':")
    print(f"   ├─ Board:   {school_board}")
    print(f"   ├─ Grade:   {grade}")
    print(f"   ├─ Chapter: {chapter_slug}")
    print(f"   └─ Phase:   {phase}")
    
    return grade, chapter_slug, phase, school_board


def download_blob_to_temp(bucket_name: str, blob_name: str) -> Path:
    """
    Downloads a raw PDF file from your Google Cloud Storage bucket
    to a temporary secure local file for text extraction.
    """
    print(f"📥 Connecting to GCS Bucket: '{bucket_name}' to fetch '{blob_name}'...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        raise FileNotFoundError(
            f"The file '{blob_name}' was not found in bucket '{bucket_name}'."
        )

    # Save to a temporary file that cleans itself up
    temp_dir = tempfile.gettempdir()
    temp_file_path = Path(temp_dir) / f"temp_{os.path.basename(blob_name)}"
    
    blob.download_to_filename(str(temp_file_path))
    print(f"✅ Downloaded successfully to temporary path: {temp_file_path}")
    return temp_file_path


def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    """
    Reads the local PDF file page-by-page and extracts clean text strings.
    """
    print("📄 Parsing PDF structure and extracting raw text pages...")
    reader = PdfReader(str(pdf_path))
    pages_text = []
    
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        clean_text = " ".join(text.split())  # Clean whitespaces and newlines
        if clean_text.strip():
            pages_text.append(clean_text)
            
    print(f"📊 Extracted text from {len(pages_text)} valid pages.")
    return pages_text


def chunk_text(pages_text: List[str], chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Splits the extracted text into overlapping chunks. Overlapping chunks
    ensure that concepts crossing page borders are not cut in half.
    """
    print(f"✂️ Chunking text (Size: {chunk_size} chars, Overlap: {overlap} chars)...")
    full_text = "\n\n".join(pages_text)
    chunks = []
    
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        chunks.append(chunk.strip())
        start += (chunk_size - overlap)
        
    print(f"📦 Created {len(chunks)} overlapping chunks.")
    return chunks


def ingest_gcs_pdf_to_rag(
    bucket_name: str,
    blob_name: str,
    grade: str | None = None,
    chapter_slug: str | None = None,
    phase: str | None = None,
    school_board: str | None = None
) -> int:
    """
    Core RAG ingestion controller. Resolves parameters dynamically from 
    GCS file path directory metadata structures if they are not explicitly passed.
    """
    # Auto-extract parameters from directory structure if not explicitly provided
    if not all([grade, chapter_slug, phase, school_board]):
        parsed_grade, parsed_chapter, parsed_phase, parsed_board = parse_metadata_from_path(blob_name)
        grade = grade or parsed_grade
        chapter_slug = chapter_slug or parsed_chapter
        phase = phase or parsed_phase
        school_board = school_board or parsed_board

    temp_file = None
    try:
        # Step 1: Download binary from bucket
        temp_file = download_blob_to_temp(bucket_name, blob_name)
        
        # Step 2: Extract text pages
        pages_text = extract_text_from_pdf(temp_file)
        if not pages_text:
            print("⚠️ No readable text found in PDF. Ingestion cancelled.")
            return 0
            
        # Step 3: Segment text into overlapping chunks
        chunks = chunk_text(pages_text)
        
        # Step 4: Define Metadata
        metadata = {
            "grade": str(grade),
            "chapter": chapter_slug,
            "phase": phase,
            "board": school_board,
            "source": blob_name
        }
        
        # Step 5: Embed & Save into Firestore via our RAG service
        print("⚡ Generating embeddings and writing batch transaction to Firestore...")
        chunks_stored = store_context_chunks(
            chunks=chunks,
            metadata=metadata,
            doc_prefix=f"gcs_{chapter_slug}_{phase}"
        )
        
        print(f"🎉 SUCCESS! Successfully indexed {chunks_stored} chunks in Firestore '/pdf_chunks'.")
        return chunks_stored
        
    except Exception as e:
        print(f"❌ Ingestion failed: {str(e)}")
        raise e
        
    finally:
        # Cleanup temp file securely
        if temp_file and temp_file.exists():
            temp_file.unlink()
            print("🧹 Cleaned up temporary system files.")


def gcs_trigger_cloud_function(event, context) -> dict:
    """
    Entry point for GCS Google Cloud Function Trigger.
    Deploys effortlessly on GCP as a standard background trigger.
    
    Compatible signature:
        - Runtime: Python 3.11+
        - Trigger type: Cloud Storage (google.storage.object.finalize)
    """
    # Google Cloud Function passes the event payload representing the GCS object metadata
    bucket_name = event.get('bucket')
    blob_name = event.get('name')

    if not blob_name.lower().endswith('.pdf'):
        print(f"⏭️ File '{blob_name}' is not a PDF asset. Skipping RAG indexing pipeline.")
        return {"status": "skipped", "reason": "not_a_pdf"}

    print(f"🚀 Automated RAG Pipeline Triggered for 'gs://{bucket_name}/{blob_name}'")
    try:
        total_indexed = ingest_gcs_pdf_to_rag(bucket_name=bucket_name, blob_name=blob_name)
        return {
            "status": "success",
            "bucket": bucket_name,
            "file": blob_name,
            "chunks_created": total_indexed
        }
    except Exception as err:
        print(f"🚨 Background Cloud Function RAG task failed: {str(err)}")
        return {"status": "failed", "error": str(err)}