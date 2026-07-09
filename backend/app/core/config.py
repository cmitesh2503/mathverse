
"""
MathVerse Configuration

Single source of truth for runtime configuration.

Rules
-----
- Do not call os.getenv() outside this file except for
  infrastructure-specific runtime detection.
- Keep this module backward compatible.
- Export constants only.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parents[2] / ".env"
)


# ==========================================================
# Helper Functions
# ==========================================================

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_flag(name: str, default: bool = False) -> bool:
    return _env(name, "true" if default else "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = _env(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# ==========================================================
# Gemini / Vertex AI
# ==========================================================

GEMINI_API_KEY = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")

DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_TEXT_MODEL = "gemini-2.5-flash-lite"

_DEPRECATED_GEMINI_TEXT_MODELS = {
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
}

_configured_text_model = _env(
    "GEMINI_TEXT_MODEL",
    DEFAULT_GEMINI_TEXT_MODEL,
)

GEMINI_TEXT_MODEL = (
    FALLBACK_GEMINI_TEXT_MODEL
    if _configured_text_model in _DEPRECATED_GEMINI_TEXT_MODELS
    else (_configured_text_model or DEFAULT_GEMINI_TEXT_MODEL)
)

DEFAULT_GEMINI_LIVE_MODEL = (
    "gemini-2.5-flash-native-audio-preview-12-2025"
)

_configured_live_model = _env(
    "GEMINI_LIVE_MODEL",
    DEFAULT_GEMINI_LIVE_MODEL,
)

GEMINI_LIVE_MODEL = (
    _configured_live_model
    if (
        "live" in _configured_live_model.lower()
        or "native-audio" in _configured_live_model.lower()
    )
    else DEFAULT_GEMINI_LIVE_MODEL
)

GEMINI_LIVE_VOICE = _env("GEMINI_LIVE_VOICE", "Puck")
GEMINI_LIVE_INPUT_LANGUAGE = _env("GEMINI_LIVE_INPUT_LANGUAGE", "en-IN")
GEMINI_LIVE_OUTPUT_LANGUAGE = _env("GEMINI_LIVE_OUTPUT_LANGUAGE", "en-IN")

GEMINI_PLANNER_MODEL = _env(
    "GEMINI_PLANNER_MODEL",
    GEMINI_TEXT_MODEL,
)

GEMINI_TTS_MODEL = _env(
    "GEMINI_TTS_MODEL",
    "gemini-2.0-flash",
)

# ==========================================================
# LiveAvatar
# ==========================================================

LIVEAVATAR_API_BASE = _env(
    "LIVEAVATAR_API_BASE",
    "https://api.liveavatar.com",
)

LIVEAVATAR_EMBED_BASE = _env(
    "LIVEAVATAR_EMBED_BASE",
    "https://meet.livekit.io/custom",
)

LIVEAVATAR_API_KEY = _env("LIVEAVATAR_API_KEY")

LIVEAVATAR_AVATAR_ID = _env("LIVEAVATAR_AVATAR_ID")

LIVEAVATAR_CONTEXT_ID = _env("LIVEAVATAR_CONTEXT_ID")

LIVEAVATAR_VOICE_ID = _env("LIVEAVATAR_VOICE_ID")

LIVEAVATAR_LANGUAGE = _env(
    "LIVEAVATAR_LANGUAGE",
    "en",
)

LIVEAVATAR_MODE = _env(
    "LIVEAVATAR_MODE",
    "FULL",
)

LIVEAVATAR_IS_SANDBOX = _env_flag(
    "LIVEAVATAR_IS_SANDBOX",
    default=True,
)

LIVEAVATAR_AUTO_START = _env_flag(
    "LIVEAVATAR_AUTO_START",
    default=False,
)

LIVEAVATAR_SPEECH_SPEED = _env_float(
    "LIVEAVATAR_SPEECH_SPEED",
    0.55,
)

# ==========================================================
# Google Cloud
# ==========================================================

GOOGLE_CLOUD_PROJECT = _env(
    "GOOGLE_CLOUD_PROJECT",
    "matverse",
)

GOOGLE_CLOUD_LOCATION = _env(
    "GOOGLE_CLOUD_LOCATION",
    "us-central1",
)

GOOGLE_CLOUD_QUOTA_PROJECT = _env(
    "GOOGLE_CLOUD_QUOTA_PROJECT",
    GOOGLE_CLOUD_PROJECT,
)

# Legacy compatibility
PROJECT_ID = GOOGLE_CLOUD_PROJECT
PROCESSOR_LOCATION = GOOGLE_CLOUD_LOCATION

# ==========================================================
# Firestore
# ==========================================================

FIRESTORE_PROJECT_ID = _env(
    "FIRESTORE_PROJECT_ID",
    GOOGLE_CLOUD_PROJECT,
)

MATHVERSE_FIRESTORE_AUTH_MODE = _env(
    "MATHVERSE_FIRESTORE_AUTH_MODE",
    "adc",
)

MATHVERSE_REQUIRED_GCLOUD_ACCOUNT = _env(
    "MATHVERSE_REQUIRED_GCLOUD_ACCOUNT",
)

MATHVERSE_ENABLE_FIREBASE = _env_flag(
    "MATHVERSE_ENABLE_FIREBASE",
    default=True,
)

# ==========================================================
# Knowledge Factory
# ==========================================================

MATHVERSE_CURRICULUM_SOURCE = _env(
    "MATHVERSE_CURRICULUM_SOURCE",
    "local",
)

MATHVERSE_EXERCISES_SOURCE = _env(
    "MATHVERSE_EXERCISES_SOURCE",
    "firestore",
)

MATHVERSE_EXERCISES_ALLOW_LOCAL_FALLBACK = _env_flag(
    "MATHVERSE_EXERCISES_ALLOW_LOCAL_FALLBACK",
    default=False,
)

MATHVERSE_LOCAL_PDF_ROOT = _env(
    "MATHVERSE_LOCAL_PDF_ROOT",
    "offline_assets/pdfs",
)

# ==========================================================
# Retrieval (RAG)
# ==========================================================

MATHVERSE_RAG_COLLECTION = _env(
    "MATHVERSE_RAG_COLLECTION",
    "pdf_chunks",
)

MATHVERSE_RAG_CACHE_TTL_SECONDS = _env_int(
    "MATHVERSE_RAG_CACHE_TTL_SECONDS",
    3600,
)

MATHVERSE_RAG_ALLOW_UNSCOPED_FALLBACK = _env_flag(
    "MATHVERSE_RAG_ALLOW_UNSCOPED_FALLBACK",
    default=False,
)

# ==========================================================
# Embeddings
# ==========================================================

MATHVERSE_EMBEDDING_MODEL = _env(
    "MATHVERSE_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

VERTEX_AI_LOCATION = _env(
    "VERTEX_AI_LOCATION",
    GOOGLE_CLOUD_LOCATION,
)

GOOGLE_CLOUD_REGION = _env(
    "GOOGLE_CLOUD_REGION",
    GOOGLE_CLOUD_LOCATION,
)

# ==========================================================
# Local AI (Development)
# ==========================================================

LOCAL_AI_API_BASE = _env(
    "LOCAL_AI_API_BASE",
    "http://localhost:11434/api/generate",
)

LOCAL_AI_MODEL = _env(
    "LOCAL_AI_MODEL",
    "qwen2.5",
)

# ==========================================================
# Cache
# ==========================================================

MATHVERSE_CACHE_BACKEND = _env(
    "MATHVERSE_CACHE_BACKEND",
    "memory",
)

MATHVERSE_CACHE_TTL_SECONDS = _env_int(
    "MATHVERSE_CACHE_TTL_SECONDS",
    86400,
)

MATHVERSE_CACHE_REQUIRE_REDIS = _env_flag(
    "MATHVERSE_CACHE_REQUIRE_REDIS",
    default=False,
)

# ==========================================================
# Redis
# ==========================================================

# Infrastructure setting.
# This intentionally remains configurable at runtime.

REDIS_URL = _env(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

# ==========================================================
# Orchestrator
# ==========================================================

ORCHESTRATOR_STORE = _env(
    "ORCHESTRATOR_STORE",
    "memory",
)

ORCHESTRATOR_SESSION_KEY_PREFIX = _env(
    "ORCHESTRATOR_SESSION_KEY_PREFIX",
    "orchestrator:session:",
)

ORCHESTRATOR_REQUIRE_REDIS = _env_flag(
    "ORCHESTRATOR_REQUIRE_REDIS",
    default=False,
)

# ==========================================================
# Runtime Feature Flags
# ==========================================================

MATHVERSE_ENABLE_TTS = _env_flag(
    "MATHVERSE_ENABLE_TTS",
    default=False,
)

MATHVERSE_ENABLE_ATTEMPT_LOGGING = _env_flag(
    "MATHVERSE_ENABLE_ATTEMPT_LOGGING",
    default=False,
)

# ==========================================================
# Development
# ==========================================================

MATHVERSE_RELOAD = _env_flag(
    "MATHVERSE_RELOAD",
    default=False,
)

APP_ENV = _env(
    "APP_ENV",
    "development",
)

APP_NAME = _env(
    "APP_NAME",
    "MathVerse",
)

APP_VERSION = _env(
    "APP_VERSION",
    "0.1.0",
)

APP_DEBUG = _env_flag(
    "APP_DEBUG",
    default=True,
)
# ==========================================================
# Legacy Compatibility
# ==========================================================
#
# These aliases allow older modules to continue functioning
# while the codebase is migrated to centralized configuration.
# New code should use the primary constants above.
#

VERTEX_TEXT_MODEL = GEMINI_TEXT_MODEL

VERTEX_LIVE_MODEL = GEMINI_LIVE_MODEL

VERTEX_INPUT_LANGUAGE = GEMINI_LIVE_INPUT_LANGUAGE

VERTEX_OUTPUT_LANGUAGE = GEMINI_LIVE_OUTPUT_LANGUAGE

VERTEX_VOICE = GEMINI_LIVE_VOICE

# ==========================================================
# Optional Service Account Paths
# ==========================================================
#
# These are intentionally kept here because they are used by
# firestore_client.py to determine authentication mode.
#

GOOGLE_APPLICATION_CREDENTIALS = _env(
    "GOOGLE_APPLICATION_CREDENTIALS",
)

FIREBASE_SERVICE_ACCOUNT_PATH = _env(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
)

# ==========================================================
# Environment Summary
# ==========================================================
#
# This module is the ONLY location in the application where
# runtime environment variables should be read.
#
# All other modules should import configuration values from:
#
#     from app.core import config
#
# Examples
#
#     config.GEMINI_TEXT_MODEL
#     config.GOOGLE_CLOUD_PROJECT
#     config.FIRESTORE_PROJECT_ID
#     config.MATHVERSE_CACHE_BACKEND
#
# Avoid calling:
#
#     os.getenv(...)
#
# outside this module except for infrastructure/runtime
# detection where explicitly required.
#
# ==========================================================

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = _env(
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
)

AZURE_DOCUMENT_INTELLIGENCE_KEY = _env(
    "AZURE_DOCUMENT_INTELLIGENCE_KEY",
)
