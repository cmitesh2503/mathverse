# Knowledge Factory source

MathVerse reads curriculum, chapter content, practice questions, and tutor retrieval context from the Knowledge Factory Firestore source. The browser never receives Google credentials.

Backend configuration:

```env
KNOWLEDGE_FACTORY_PROJECT_ID=knowledge-factory-prod
KNOWLEDGE_FACTORY_DATABASE_ID=(default)
KNOWLEDGE_FACTORY_PACKAGE_COLLECTION=knowledge_packages
KNOWLEDGE_FACTORY_VECTOR_COLLECTION=knowledge_vectors
# Optional when package metadata does not contain subject/grade/board:
KNOWLEDGE_FACTORY_DOCUMENT_ID=
MATHVERSE_FIRESTORE_AUTH_MODE=adc
GOOGLE_APPLICATION_CREDENTIALS=
```

Use ADC locally (`gcloud auth application-default login`) or provide a workload identity/service-account path to the backend runtime. Grant the runtime read access to the Knowledge Factory project/database. MathVerse does not use the old `matverse` knowledge collections, `pdf_chunks`, local curriculum JSON, or local knowledge-package files as a fallback.
# MathVerse

MathVerse is a classroom-style CBSE mathematics tutor with:

- Gemini Live tutor conversation
- persistent session memory
- whiteboard-guided lessons
- provider-ready human avatar support

## Key Avatar Backend Vars

```env
LIVEAVATAR_API_KEY=...
LIVEAVATAR_AVATAR_ID=...
LIVEAVATAR_CONTEXT_ID=...
LIVEAVATAR_VOICE_ID=...
LIVEAVATAR_LANGUAGE=en
LIVEAVATAR_IS_SANDBOX=true
LIVEAVATAR_AUTO_START=false
LIVEAVATAR_SPEECH_SPEED=0.78
```

Frontend setup is documented in `mathverse-frontend/README.md`.
See `backend/.env.example` for backend environment variables and `mathverse-frontend/.env.local.example` for frontend avatar provider settings.
