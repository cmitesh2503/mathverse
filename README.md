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
