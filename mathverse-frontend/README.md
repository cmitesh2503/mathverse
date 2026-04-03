# MathVerse Frontend

MathVerse is a classroom-style CBSE mathematics tutor with:

- real-time tutor audio
- session memory and class archive
- whiteboard-guided explanations
- provider-ready human avatar support

## Local Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Human Avatar Setup

### Recommended: LiveAvatar

MathVerse now has a provider-specific path for LiveAvatar. The backend can create and start a LiveAvatar session, then the frontend loads the returned human-video room inside the classroom.

Backend environment:

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

Copy `.env.local.example` to `.env.local` and choose one provider:

```bash
cp .env.local.example .env.local
```

Then set one of these:
For LiveAvatar:

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=liveavatar
```

Then use the `Start Human Avatar` button in the classroom.

### Other Providers

### HeyGen

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=heygen
NEXT_PUBLIC_HEYGEN_AVATAR_IFRAME_URL=https://...
```

### Tavus

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=tavus
NEXT_PUBLIC_TAVUS_AVATAR_IFRAME_URL=https://...
```

### D-ID

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=did
NEXT_PUBLIC_DID_AVATAR_IFRAME_URL=https://...
```

### Custom Iframe

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=custom
NEXT_PUBLIC_TUTOR_AVATAR_IFRAME_URL=https://...
```

### Hosted Video

```env
NEXT_PUBLIC_TUTOR_AVATAR_PROVIDER=video
NEXT_PUBLIC_TUTOR_AVATAR_VIDEO_SRC=https://...
```

If no avatar URL is configured, MathVerse falls back to the built-in teacher illustration.
