#!/usr/bin/env python3
"""
Migrate CBSE exercises from local PDFs to Firestore.

This script reads exercises from local PDF files and stores them in Firestore
for easier retrieval and reduced local storage dependency.

Usage:
    python migrate_exercises_to_firestore.py [--grade 10] [--chapter 1] [--dry-run]
"""

import sys
import argparse
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MATHVERSE_EXERCISES_SOURCE", "local")
os.environ.setdefault("MATHVERSE_LOCAL_PDF_ROOT", str(BACKEND_DIR / "offline_assets" / "pdfs"))

try:
    from app.services.cbse_exercises import (
        load_chapter_pdf_exercises,
        load_chapter_pdf_theory,
        GRADE_10_PDF_CHAPTERS,
    )
    from app.services.firestore_exercises import (
        store_chapter_exercises,
        store_chapter_theory,
    )
except ModuleNotFoundError:
    # Handle relative imports from CLI
    sys.path.insert(0, str(BACKEND_DIR))
    
    from app.services.cbse_exercises import (
        load_chapter_pdf_exercises,
        load_chapter_pdf_theory,
        GRADE_10_PDF_CHAPTERS,
    )
    from app.services.firestore_exercises import (
        store_chapter_exercises,
        store_chapter_theory,
    )


def migrate_chapter(
    grade: int,
    chapter_index: int,
    chapter_title: str,
    dry_run: bool = False,
) -> bool:
    """
    Migrate a single chapter's exercises and theory to Firestore.
    
    Returns:
        True if successful, False otherwise.
    """
    print(f"\nMigrating Grade {grade}, Chapter {chapter_index}: {chapter_title}")
    
    # Load from local PDF
    try:
        print("  Loading exercises from local PDF...")
        problems = load_chapter_pdf_exercises(grade, chapter_index, chapter_title)
        print(f"  Loaded {len(problems)} problems")
    except Exception as e:
        print(f"  Failed to load exercises: {e}")
        return False
    
    try:
        print("  Loading theory from local PDF...")
        theory = load_chapter_pdf_theory(grade, chapter_index)
        print(f"  Loaded {len(theory)} characters of theory content")
    except Exception as e:
        print(f"  Failed to load theory (continuing): {e}")
        theory = ""

    if dry_run:
        print(f"  [DRY RUN] Would store {len(problems)} problems and {len(theory)} chars of theory")
        return True
    
    # Store to Firestore
    try:
        print("  Storing exercises to Firestore...")
        if not store_chapter_exercises(grade, chapter_index, chapter_title, problems):
            print("  Failed to store exercises")
            return False
        print("  Exercises stored")
    except Exception as e:
        print(f"  Failed to store exercises: {e}")
        return False
    
    if theory:
        try:
            print("  Storing theory to Firestore...")
            if not store_chapter_theory(grade, chapter_index, theory):
                print("  Failed to store theory")
            else:
                print("  Theory stored")
        except Exception as e:
            print(f"  Failed to store theory: {e}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate CBSE exercises from local PDFs to Firestore"
    )
    parser.add_argument(
        "--grade",
        type=int,
        default=10,
        help="Grade to migrate (default: 10)",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        help="Specific chapter to migrate (if not set, migrates all chapters)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually storing",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )
    
    args = parser.parse_args()
    
    print("CBSE Exercise Migration to Firestore")
    print(f"   Grade: {args.grade}")
    if args.chapter:
        print(f"   Chapter: {args.chapter}")
    else:
        print(f"   Chapters: All available")
    if args.dry_run:
        print("   Mode: DRY RUN")
    print()
    
    # Determine chapters to migrate
    if args.chapter:
        chapters_to_migrate = [(args.chapter, f"Chapter {args.chapter}")]
    else:
        if args.grade == 10:
            chapters_to_migrate = [
                (idx, title)
                for title, idx in sorted(GRADE_10_PDF_CHAPTERS.items(), key=lambda x: x[1])
            ]
        else:
            print(f"Grade {args.grade} not configured. Provide --chapter manually.")
            return 1
    
    # Migrate each chapter
    success_count = 0
    fail_count = 0
    
    for chapter_index, chapter_title in chapters_to_migrate:
        if migrate_chapter(args.grade, chapter_index, chapter_title, args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"Successfully migrated: {success_count} chapters")
    if fail_count > 0:
        print(f"Failed: {fail_count} chapters")
    print(f"{'=' * 60}\n")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    exit(main())
