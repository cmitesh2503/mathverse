#!/usr/bin/env python
"""
Simplified PDF workflow test - verifies structure without API calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.pdf_processor import chunk_text
from app.services.retrieval_service import load_chunks

def test_pdf_workflow():
    """Test PDF workflow - chunking and data structure."""
    
    print("=" * 80)
    print("PDF INGESTION WORKFLOW TEST")
    print("=" * 80)
    
    # Sample curriculum text
    sample_text = """
    PAIR OF LINEAR EQUATIONS IN TWO VARIABLES
    
    Chapter 3: Linear Equations
    
    Introduction:
    Linear equations are fundamental to algebra. A linear equation in two variables
    is an equation that can be written in the form ax + by + c = 0, where a, b, c
    are real numbers and a and b are not both zero.
    
    Definition:
    An equation of the form ax + by + c = 0, where a, b, c are real numbers and
    a ≠ 0, b ≠ 0, is called a linear equation in two variables x and y.
    
    Solution Methods:
    1. Elimination Method: Eliminate one variable by addition/subtraction
    2. Substitution Method: Solve one equation for one variable and substitute
    3. Cross-multiplication Method: Use the formula for solving linear equations
    4. Graphical Method: Plot graphs and find intersection point
    
    Consistency and Independence:
    A system of linear equations is consistent if it has at least one solution.
    It is inconsistent if it has no solution. A system is independent if it has
    exactly one solution, and dependent if it has infinitely many solutions.
    """
    
    print("\n✓ TEST 1: TEXT CHUNKING")
    print("-" * 80)
    
    grade = 10
    topic = "pair_of_linear_equations_in_two_variables"
    subject = "Mathematics"
    source = "NCERT_Grade_10_Mathematics_Chapter_3"
    
    chunks = chunk_text(
        sample_text,
        grade=grade,
        subject=subject,
        topic=topic,
        source=source
    )
    
    print(f"Chunked {len(chunks)} segments")
    print(f"  Grade: {grade}")
    print(f"  Topic: {topic}")
    print(f"  Subject: {subject}")
    print(f"  Source: {source}")
    
    # Verify chunk structure
    first_chunk = chunks[0]
    expected_keys = {"text", "grade", "subject", "topic", "source"}
    actual_keys = set(first_chunk.keys())
    
    if expected_keys == actual_keys:
        print(f"\n✓ Chunk structure valid")
        print(f"  Keys: {sorted(actual_keys)}")
    else:
        print(f"✗ Chunk structure mismatch")
        print(f"  Expected: {sorted(expected_keys)}")
        print(f"  Got: {sorted(actual_keys)}")
        return False
    
    # Display first chunk details
    print(f"\n✓ First chunk preview:")
    print(f"  Text length: {len(first_chunk['text'])} chars")
    print(f"  Grade: {first_chunk['grade']}")
    print(f"  Topic: {first_chunk['topic']}")
    print(f"  Source: {first_chunk['source']}")
    print(f"  Text: {first_chunk['text'][:120]}...")
    
    print("\n✓ TEST 2: CHUNK METADATA VERIFICATION")
    print("-" * 80)
    
    # Verify all chunks have correct metadata
    all_valid = True
    for i, chunk in enumerate(chunks):
        if chunk['grade'] != grade:
            print(f"✗ Chunk {i}: Grade mismatch - {chunk['grade']} != {grade}")
            all_valid = False
        if chunk['topic'] != topic:
            print(f"✗ Chunk {i}: Topic mismatch - {chunk['topic']} != {topic}")
            all_valid = False
        if chunk['subject'] != subject:
            print(f"✗ Chunk {i}: Subject mismatch - {chunk['subject']} != {subject}")
            all_valid = False
    
    if all_valid:
        print(f"✓ All {len(chunks)} chunks have correct metadata")
    else:
        return False
    
    print("\n✓ TEST 3: FALLBACK RETRIEVAL DATA")
    print("-" * 80)
    
    try:
        fallback_chunks = load_chunks()
        print(f"✓ Fallback data loaded: {len(fallback_chunks)} chunks in ncert_chunks.json")
        if fallback_chunks:
            print(f"  Sample chunk keys: {list(fallback_chunks[0].keys())}")
    except Exception as e:
        print(f"⊘ Fallback data not found (expected if no PDFs processed yet): {e}")
    
    print("\n✓ TEST 4: CHROMADB READINESS")
    print("-" * 80)
    
    chroma_path = "./chroma_db"
    if os.path.exists(chroma_path):
        print(f"✓ ChromaDB directory exists: {chroma_path}")
        print(f"  This is where embeddings will be persisted")
    else:
        print(f"⊘ ChromaDB directory not yet created")
        print(f"  Will be created when first PDFs are processed")
    
    print("\n" + "=" * 80)
    print("✓ PDF WORKFLOW VERIFICATION COMPLETE")
    print("=" * 80)
    
    print("\n📋 WORKFLOW SUMMARY:")
    print("─" * 80)
    print(f"""
1. INPUT: NCERT/CBSE PDF files (Math, Science, etc.)
2. PROCESS: 
   • Extract text from PDF
   • Split into {len(chunks)} chunks (1000 tokens each, 200 overlap)
   • Embed each chunk with Gemini embedding model
   • Store in ChromaDB with metadata: grade, topic, subject, source

3. STORAGE & RETRIEVAL:
   • ChromaDB path: ./chroma_db (persistent, survives restarts)
   • Collection: "cbse_curriculum"
   • Fallback: ncert_chunks.json

4. USAGE IN LIVE TUTOR:
   • When student starts session on a topic
   • System retrieves top 5 relevant chunks for that grade/topic
   • Chunks injected into Gemini system prompt (max 1800 chars)
   • Gemini uses PDF content to teach

5. EXAMPLE USAGE:
   from backend.app.services.pdf_processor import process_pdf
   
   process_pdf(
       "NCERT_Grade_10_Math.pdf",
       grade=10,
       topic="pair_of_linear_equations_in_two_variables",
       subject="Mathematics",
       source="NCERT_Grade_10_Mathematics"
   )
""")
    
    print("\n✓ System is ready to process NCERT/CBSE PDFs!")
    print("  Next: Upload PDFs and run process_pdf() to ingest them")
    
    return True

if __name__ == "__main__":
    success = test_pdf_workflow()
    sys.exit(0 if success else 1)
