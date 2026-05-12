from __future__ import annotations

import asyncio
import json
from functools import lru_cache

from ..cache.cache_manager import get_cache, set_cache
from ..core.config import GEMINI_API_KEY, GEMINI_LIVE_MODEL, GEMINI_TEXT_MODEL
from ..guardrails.ai_guardrail import validate_response

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover - optional dependency
    google_genai = None

try:
    import google.generativeai as legacy_genai
except ImportError:  # pragma: no cover - optional dependency
    legacy_genai = None

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:  # pragma: no cover - optional dependency
    ResourceExhausted = None


TEXT_MODEL_ID = "gemini-3.1-flash-lite"
DEPRECATED_TEXT_MODEL_SUFFIXES = ("2.0-flash", "2.0-flash-001")

DEFAULT_TEXT_MODEL = (
    TEXT_MODEL_ID
    if GEMINI_TEXT_MODEL in {f"gemini-{suffix}" for suffix in DEPRECATED_TEXT_MODEL_SUFFIXES}
    else GEMINI_TEXT_MODEL
)
DEFAULT_LIVE_MODEL = GEMINI_LIVE_MODEL

SAFE_FALLBACK_AGENT_RESPONSE = {
    "spoken_response": "I'm sorry, I'm experiencing heavy traffic right now and need a moment to catch my breath. Let's pause for a minute.",
    "whiteboard_actions": [],
}
FALLBACK_TEXT = json.dumps(SAFE_FALLBACK_AGENT_RESPONSE)


def live_api_available() -> bool:
    return bool(GEMINI_API_KEY and google_genai is not None)


@lru_cache(maxsize=1)
def _new_sdk_client():
    if not GEMINI_API_KEY or google_genai is None:
        return None
    return google_genai.Client(api_key=GEMINI_API_KEY)


def get_live_client():
    return _new_sdk_client()


def _configure_legacy_sdk() -> bool:
    if not GEMINI_API_KEY or legacy_genai is None:
        return False
    legacy_genai.configure(api_key=GEMINI_API_KEY)
    return True


def _normalize_model_id(model: str | None) -> str:
    deprecated_model_ids = {f"gemini-{suffix}" for suffix in DEPRECATED_TEXT_MODEL_SUFFIXES}
    if not model or model in deprecated_model_ids:
        return TEXT_MODEL_ID
    return model


def _fallback_json() -> str:
    return json.dumps(SAFE_FALLBACK_AGENT_RESPONSE)


def _is_quota_error(error: Exception) -> bool:
    if ResourceExhausted is not None and isinstance(error, ResourceExhausted):
        return True

    code = getattr(error, "code", None)
    status = getattr(error, "status", None)
    message = str(error).lower()

    return (
        code == 429
        or status == "RESOURCE_EXHAUSTED"
        or "resource_exhausted" in message
        or "429" in message
        or "quota" in message
    )


def _handle_generation_error(error: Exception, *, source: str, prompt: str) -> str | None:
    if _is_quota_error(error):
        fallback = _fallback_json()
        set_cache(prompt, fallback)
        print(f"{source} quota exhausted; returning safe fallback response.")
        return fallback

    print(f"{source} error: {error}")
    return None


def generate_response(prompt: str, model: str = DEFAULT_TEXT_MODEL) -> str:
    cached = get_cache(prompt)
    if cached:
        return cached

    model_id = _normalize_model_id(model)
    text: str | None = None

    try:
        client = _new_sdk_client()
        if client is not None:
            response = client.models.generate_content(model=model_id, contents=prompt)
            text = getattr(response, "text", None)
    except Exception as error:  # pragma: no cover - network dependent
        fallback = _handle_generation_error(error, source="GenAI SDK", prompt=prompt)
        if fallback is not None:
            return fallback

    if text is None:
        try:
            if _configure_legacy_sdk():
                legacy_model = legacy_genai.GenerativeModel(model_id)
                response = legacy_model.generate_content(prompt)
                text = getattr(response, "text", None)
        except Exception as error:  # pragma: no cover - network dependent
            fallback = _handle_generation_error(error, source="Legacy Gemini SDK", prompt=prompt)
            if fallback is not None:
                return fallback

    final_text = validate_response(text or FALLBACK_TEXT)
    set_cache(prompt, final_text)
    return final_text


async def stream_response(prompt: str, model: str = DEFAULT_TEXT_MODEL):
    text = generate_response(prompt, model=model)
    for word in text.split():
        yield word + " "
        await asyncio.sleep(0.01)
