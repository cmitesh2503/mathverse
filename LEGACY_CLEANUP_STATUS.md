# Legacy Cleanup Status - Mathverse RAG Migration

Date: 2026-06-05
Status: Firestore-first runtime; local PDF assets archived outside application code.

## Completed

- Removed the legacy FAISS rebuild/index paths from the active backend.
- Moved old PDF ingestion/processing scripts out of `backend/app/services/` into `backend/legacy_pdf_tooling/`.
- Moved the obsolete PDF workflow check into `backend/legacy_pdf_tooling/pdf_workflow_check_legacy.py`.
- Moved local PDF assets out of `backend/app/data/` into ignored offline storage:
  - `backend/offline_assets/pdfs/curriculum/cbse/`
  - `backend/offline_assets/pdfs/std_10/`
- Updated `backend/app/services/cbse_exercises.py` to default to Firestore exercise/theory retrieval.
- Kept local PDF access available only when explicitly enabled with:
  - `MATHVERSE_EXERCISES_SOURCE=local`, or
  - `MATHVERSE_EXERCISES_SOURCE=firestore` plus `MATHVERSE_EXERCISES_ALLOW_LOCAL_FALLBACK=true`

## Runtime Sources

| Feature | Runtime source | Local fallback |
| --- | --- | --- |
| RAG context | Firestore vector collection `pdf_chunks` | None |
| CBSE exercises | Firestore collection `cbse_practice_problems` | Disabled by default |
| CBSE theory | Firestore collection `cbse_theory_content` | Disabled by default |
| Curriculum JSON | `backend/app/data/curriculum/*.json` | Still local metadata |

## Offline Assets

PDFs are no longer stored under `backend/app`. They remain available locally under
`backend/offline_assets/pdfs/` for re-migration or manual recovery, but this path is
ignored by git so the application code stays clean.

The migration script sets local mode automatically:

```powershell
python backend/migrate_exercises_to_firestore.py --grade 10 --dry-run
```

To use the offline PDFs in development, set:

```dotenv
MATHVERSE_EXERCISES_SOURCE=local
MATHVERSE_LOCAL_PDF_ROOT=offline_assets/pdfs
```

## Current GCP/Firebase Contract

- Project: `mathverse-529eb`
- Region: `us-central1`
- Required ADC account in example config: `miteshc527@gmail.com`
- RAG collection: `pdf_chunks`

## Follow-up Checks

- Confirm `cbse_practice_problems` and `cbse_theory_content` are populated in Firestore.
- Run backend tutor flows with `MATHVERSE_EXERCISES_SOURCE=firestore`.
- Keep `backend/offline_assets/` out of commits.
