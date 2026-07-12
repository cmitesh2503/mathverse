# MathVerse Knowledge Factory Architecture

Version: 1.0

Status: Source of Truth

Owner: MathVerse AI

---

# Vision

The Knowledge Factory transforms educational content into a structured,
AI-ready Knowledge Graph.

Supported inputs include:

- NCERT Books
- JEE Books
- Coaching Material
- PYQs
- Teacher Notes
- Formula Sheets
- Revision Notes

The Knowledge Factory is cloud-native and event-driven.

---

# High-Level Architecture

                Teacher/Admin

                      │

                      ▼

          Google Cloud Storage

                      │

             Object Finalized Event

                      │

                  Eventarc

                      │

                      ▼

          Knowledge Dispatcher

               (Cloud Run)

                      │

                      ▼

        Firestore Processing Job

          Status = QUEUED

                      │

                      ▼

         Knowledge Worker

          (Cloud Run Job)

                      │

                      ▼

              PDF Chunker

                      │

                      ▼

      Azure Document Intelligence

          (Layout Markdown)

                      │

                      ▼

            Markdown Merger

                      │

                      ▼

             Chapter Parser

                      │

                      ▼

             Section Parser

                      │

                      ▼

        Knowledge Extractors

            ├ Concepts
            ├ Formulas
            ├ Examples
            ├ Exercises
            ├ Figures
            ├ Teacher Scripts
            ├ Whiteboard Steps
            ├ Prerequisites
            ├ Misconceptions
            └ Embeddings

                      │

                      ▼

          Firestore Knowledge Graph

---

# Google Cloud Storage

Bucket

gs://mathverse-knowledge

Structure

curriculum/

    jee/

        mathematics/

            chapter_003/

                Matrices.pdf

Temporary processing

processing/

    chapter_003/

        chunk_001.pdf

        chunk_001.md

        chunk_001.json

        merged.md

Processing artifacts may be automatically deleted
using GCS Lifecycle Rules.

---

# Firestore

curriculums/

    jee-main-2026-mathematics/

        chapters/

            chapter-003/

                metadata

                sections/

                concepts/

                formulas/

                examples/

                exercises/

                figures/

                teacher_scripts/

                whiteboard_steps/

                misconceptions/

                prerequisites/

                embeddings/

---

# Processing Jobs

processing_jobs/

    job_id

        curriculum

        chapter

        uploaded_by

        uploaded_at

        status

        stage

        progress

        started_at

        completed_at

        error

Status

QUEUED

RUNNING

FAILED

COMPLETED

Stages

UPLOAD

CHUNKING

OCR

MARKDOWN_MERGE

PARSING

SECTION_EXTRACTION

CONCEPT_EXTRACTION

FORMULA_EXTRACTION

EXAMPLE_EXTRACTION

EXERCISE_EXTRACTION

FIGURE_EXTRACTION

EMBEDDING_GENERATION

FIRESTORE_WRITE

DONE

---

# PDF Chunker

Input

One PDF

Output

chunk_001.pdf

chunk_002.pdf

...

Responsibilities

Read PDF

Split into two-page chunks

No OCR

No AI

No Firestore

---

# Azure Layout Service

Input

One PDF chunk

Output

Markdown

JSON

Responsibilities

Call Azure Layout API

Persist Markdown

Persist JSON

Return Markdown

---

# Markdown Merger

Input

chunk_001.md

chunk_002.md

...

Output

merged.md

Responsibilities

Merge markdown

Preserve page order

No parsing

---

# Chapter Parser

Input

merged.md

Output

ChapterKnowledge

Responsibilities

Extract metadata

Extract chapter title

Extract chapter number

Store raw markdown

---

# Section Parser

Input

ChapterKnowledge

Output

Sections

Responsibilities

Detect headings

Detect numbering

Create hierarchy

---

# Extractor Pipeline

Order

ConceptExtractor

FormulaExtractor

ExampleExtractor

ExerciseExtractor

FigureExtractor

TeacherScriptExtractor

WhiteboardExtractor

PrerequisiteExtractor

MisconceptionExtractor

EmbeddingBuilder

Each extractor

Receives

ChapterKnowledge

Returns

Updated ChapterKnowledge

Extractors never write to Firestore.

---

# Firestore Writer

Receives

Complete ChapterKnowledge

Writes

Metadata

Sections

Concepts

Formulas

Examples

Exercises

Figures

Teacher Scripts

Whiteboard Steps

Embeddings

Single responsibility

Persistence only

---

# Design Principles

Single Responsibility

Cloud Native

Event Driven

Idempotent

Retry Safe

Stateless Workers

Independent Extractors

Technology Independent

Easy to Replace Azure OCR

Easy to Replace Gemini

Easy to Replace Firestore

---

# Future Roadmap

Phase 1

NCERT

Phase 2

JEE

Phase 3

NEET

Phase 4

Teacher Uploads

Phase 5

Publisher Content

Phase 6

Automatic Curriculum Updates

---

# Success Criteria

A single PDF upload should automatically produce

Structured Firestore Knowledge Graph

Teacher Scripts

Whiteboard Steps

Embeddings

Ready-to-use AI Tutor Context

without manual intervention.