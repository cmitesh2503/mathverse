# Architecture Decision Log

Decision 001

Teacher Brain remains the central teaching decision engine.

Decision 002

Tutor Engine remains the orchestration layer.

Decision 003

Knowledge Platform owns all educational content.

Decision 004

Student Platform owns learning state.

Decision 005

Cloud Storage stores raw educational documents.

Decision 006

Firestore stores structured knowledge.

Decision 007

Cloud Run Functions trigger knowledge ingestion.

Decision 008

Tutor Brain never reads PDFs directly.

Decision 009

Prompt Builder never accesses Firestore.

Decision 010

Business logic never exists inside API routes.