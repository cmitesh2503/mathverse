from __future__ import annotations

import asyncio
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


DEFAULT_TEXT_MODEL = GEMINI_TEXT_MODEL
DEFAULT_LIVE_MODEL = GEMINI_LIVE_MODEL
FALLBACK_TEXT = "Let's work through that step by step."


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


def generate_response(prompt: str, model: str = DEFAULT_TEXT_MODEL) -> str:
    cached = get_cache(prompt)
    if cached:
        return cached

    text: str | None = None

    try:
        client = _new_sdk_client()
        if client is not None:
            response = client.models.generate_content(model=model, contents=prompt)
            text = getattr(response, "text", None)
    except Exception as error:  # pragma: no cover - network dependent
        print(f"GenAI SDK error: {error}")

    if text is None:
        try:
            if _configure_legacy_sdk():
                legacy_model = legacy_genai.GenerativeModel(model)
                response = legacy_model.generate_content(prompt)
                text = getattr(response, "text", None)
        except Exception as error:  # pragma: no cover - network dependent
            print(f"Legacy Gemini SDK error: {error}")

    final_text = validate_response(text or FALLBACK_TEXT)
    set_cache(prompt, final_text)
    return final_text


async def stream_response(prompt: str, model: str = DEFAULT_TEXT_MODEL):
    text = generate_response(prompt, model=model)
    for word in text.split():
        yield word + " "
        await asyncio.sleep(0.01)
