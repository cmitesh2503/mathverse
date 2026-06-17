# Legacy PDF Tooling

These files are archived for reference only. The active backend uses Firestore
RAG retrieval through `backend/app/services/rag_service.py` and Firestore-backed
exercise/theory loaders.

Local PDFs now live outside `backend/app` at `backend/offline_assets/pdfs/`.
That directory is ignored by git and should only be used for one-off migration
or recovery work.
