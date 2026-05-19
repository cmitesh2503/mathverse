from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import re
import time
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


TEXT_MODEL_ID = "gemini-3.1-flash-lite-preview"
TTS_MODEL_ID = "gemini-2.5-flash-preview-tts"
DEPRECATED_TEXT_MODEL_SUFFIXES = (
    "2.0-flash",
    "2.0-flash-001",
    "2.5-flash",
    "2.5-pro",
    "3.1-flash",
    "3.1-flash-lite",
    "3.1-pro",
    "1.5-pro",
)

DEFAULT_TEXT_MODEL = (
    TEXT_MODEL_ID
    if GEMINI_TEXT_MODEL in {f"gemini-{suffix}" for suffix in DEPRECATED_TEXT_MODEL_SUFFIXES}
    else GEMINI_TEXT_MODEL
)
DEFAULT_LIVE_MODEL = GEMINI_LIVE_MODEL
_tts_retry_after = 0.0

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


def _extract_audio_bytes_from_response(response: object) -> bytes:
    if response is None:
        return b""

    # Some SDKs expose direct bytes on response.audio.
    direct_audio = getattr(response, "audio", None)
    if isinstance(direct_audio, (bytes, bytearray)):
        return bytes(direct_audio)

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            if inline is not None:
                data = getattr(inline, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception:
                        pass
            audio = getattr(part, "audio", None)
            if isinstance(audio, (bytes, bytearray)):
                return bytes(audio)

    return b""


def _generate_audio_sync(transcript: str, voice_name: str) -> bytes:
    global _tts_retry_after
    if time.monotonic() < _tts_retry_after:
        return b""

    client = _new_sdk_client()
    if client is None:
        return b""

    tts_prompt = (
        "You are Arvind Sir, an Indian Math Tutor. "
        f"Deliver this transcript naturally: {transcript}"
    )

    # Prefer typed config when available, fallback to plain dict.
    config: object
    try:
        from google.genai import types as genai_types  # type: ignore

        config = genai_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )
    except Exception:
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": voice_name,
                    }
                }
            },
        }

    try:
        response = client.models.generate_content(
            model=TTS_MODEL_ID,
            contents=tts_prompt,
            config=config,
        )
        return _extract_audio_bytes_from_response(response)
    except Exception as error:
        if _is_quota_error(error):
            retry_delay = 60.0
            retry_match = re.search(r"retry(?: in|Delay['\"]?:\s*['\"]?)\s*(\d+(?:\.\d+)?)s", str(error), re.IGNORECASE)
            if retry_match:
                with contextlib.suppress(ValueError):
                    retry_delay = max(10.0, float(retry_match.group(1)))
            _tts_retry_after = time.monotonic() + retry_delay
        print(f"TTS Rate Limit or Quota Exhausted: {error}. Proceeding with clean text execution.")
        return b""


async def generate_audio(transcript: str, voice_name: str = "Algenib") -> bytes:
    text = str(transcript or "").strip()
    if not text:
        return b""
    return await asyncio.to_thread(_generate_audio_sync, text, voice_name)
