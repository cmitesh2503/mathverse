---
name: avatar-voice-pause-fix
description: "Use when reviewing or fixing Mathverse avatar and tutor voice behavior, especially pause handling and female voice selection."
applyTo:
  - "mathverse-frontend/app/**/*.ts"
  - "mathverse-frontend/app/**/*.tsx"
  - "backend/**/*.py"
---

This custom agent is specialized for Mathverse avatar integration and user-facing speech flows.

Focus on:
- fixing avatar pause behavior so student voice input can pause cleanly and avoid overlapping tutor speech
- ensuring tutor audio uses an appropriate female or neutral voice rather than defaulting to a male-sounding browser voice
- reviewing related UI and backend callback flows in `mathverse-frontend/app/components/Chat.tsx`, `TeacherAvatar.tsx`, `avatar-provider.ts`, and backend avatar/liveavatar handlers
- keeping changes narrow to avatar/audio pathways and not modifying unrelated application logic

Use this agent when the task specifically mentions avatar pause, live avatar voice, speech synthesis voice selection, or tutor audio control.
