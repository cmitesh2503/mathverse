# MathVerse Request Flow

This document describes how a student interaction flows through the system.

All tutoring requests must follow this architecture.

----------------------------------------------------

Student

↓

Frontend (Next.js)

↓

FastAPI API

↓

Tutor Engine

↓

Tutor Context

↓

Teacher Brain

↓

Knowledge Platform

↓

Prompt Builder

↓

Vertex AI Gemini

↓

Teacher Memory Update

↓

Student Session Update

↓

Response Formatter

↓

Frontend

----------------------------------------------------

Only Tutor Engine orchestrates the tutoring flow.

Teacher Brain makes teaching decisions.

Knowledge Platform provides educational content.

Student Platform stores learning state.

Analytics Platform records learning events.

Infrastructure Platform stores data.