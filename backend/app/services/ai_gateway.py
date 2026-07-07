from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
import random
import re
import time
from functools import lru_cache
from typing import Any
from app.core import config

# Production/ADC-first configuration: do not automatically load .env files here.
# Local development may still use a separate startup script to load env vars.

from ..cache.cache_manager import get_cache, set_cache
from ..core.config import GEMINI_LIVE_MODEL, GEMINI_TEXT_MODEL
from ..guardrails.ai_guardrail import validate_response

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:  # pragma: no cover - optional dependency
    ResourceExhausted = None


# GEMINI_API_KEY is not required in production when using ADC/Vertex AI.
# Keep as None to avoid code paths that expect an explicit key.
GEMINI_API_KEY = None

TEXT_MODEL_ID = "gemini-2.5-flash"
TTS_MODEL_ID = config.GEMINI_TTS_MODEL
DEPRECATED_TEXT_MODEL_SUFFIXES = (
    "1.5-flash",
    "1.5-flash-8b",
    "1.5-pro",
)

GEMINI_TEXT_MODEL_ENV = config.GEMINI_TEXT_MODEL
DEFAULT_TEXT_MODEL = (
    TEXT_MODEL_ID
    if GEMINI_TEXT_MODEL_ENV in {f"gemini-{suffix}" for suffix in DEPRECATED_TEXT_MODEL_SUFFIXES}
    else GEMINI_TEXT_MODEL_ENV
)
DEFAULT_LIVE_MODEL = GEMINI_LIVE_MODEL
GENAI_HTTP_TIMEOUT_MS = 300_000
_tts_retry_after = 0.0


@lru_cache(maxsize=1)
def _google_genai_module():
    try:
        from google import genai as google_genai
    except ImportError:  # pragma: no cover - optional dependency
        return None
    return google_genai


@lru_cache(maxsize=1)
def _legacy_genai_module():
    try:
        import google.generativeai as legacy_genai
    except ImportError:  # pragma: no cover - optional dependency
        return None
    return legacy_genai


SAFE_FALLBACK_AGENT_RESPONSE = {
    "spoken_response": "I'm sorry, I'm experiencing heavy traffic right now and need a moment to catch my breath. Let's pause for a minute.",
    "whiteboard_actions": [],
}
FALLBACK_TEXT = json.dumps(SAFE_FALLBACK_AGENT_RESPONSE)


def live_api_available() -> bool:
    """Verifies if the live GenAI API keys and modules are active."""
    return bool(_has_active_auth() and _google_genai_module() is not None)


@lru_cache(maxsize=1)
def _new_sdk_client():
    google_genai = _google_genai_module()

    if google_genai is None:
        return None

    project = config.GOOGLE_CLOUD_PROJECT
    location = config.GOOGLE_CLOUD_LOCATION
    return google_genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )


def get_live_client():
    """Provides the active Google GenAI SDK client for WebSockets and live media streams."""
    return _new_sdk_client()


def _configure_legacy_sdk() -> bool:
    # Legacy client is only configured when an explicit API key is provided.
    # In ADC-first deployments this will usually be False.
    legacy_genai = _legacy_genai_module()
    if legacy_genai is None:
        return False
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return False
    legacy_genai.configure(api_key=api_key)
    return True


def _normalize_model_id(model: str | None) -> str:
    if not model:
        return TEXT_MODEL_ID
    model = model.replace("models/", "")
    deprecated_model_ids = {f"gemini-{suffix}" for suffix in DEPRECATED_TEXT_MODEL_SUFFIXES}
    if model in deprecated_model_ids:
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


def _is_transient_error(error: Exception) -> bool:
    """Detects temporarily overloaded service and transient back-end connection anomalies."""
    message = str(error).lower()
    return (
        "503" in message 
        or "unavailable" in message 
        or "high demand" in message 
        or "overloaded" in message
    )


def _handle_generation_error(error: Exception, *, source: str, prompt: str) -> str | None:
    if _is_quota_error(error):
        fallback = _fallback_json()
        set_cache(prompt, fallback)
        print(f"{source} quota exhausted; returning safe fallback response.")
        return fallback

    print(f"{source} error: {error}")
    return None


@lru_cache(maxsize=1)
def _has_adc_credentials() -> bool:
    try:
        import google.auth
        credentials, _ = google.auth.default()
        return credentials is not None
    except Exception:
        return False


def _has_active_auth() -> bool:
    return _has_adc_credentials()

def generate_image_response(
    prompt,
    image_bytes
):    client = _new_sdk_client()
  

def generate_response(
    prompt: str, 
    model: str = DEFAULT_TEXT_MODEL, 
    response_schema: Any = None
) -> str:
    """
    Primary completion gateway. Implements up to 5 automatic retry turns with
    jittered exponential delays to handle peak traffic demand (503s & 429s).
    """
    cached = get_cache(prompt)
    if cached:
        return cached

    if response_schema and not _has_active_auth():
        raise RuntimeError(
            "Structured response generation requires Application Default Credentials (ADC) with Vertex AI access. "
            "Deploy the app with a service account that has Vertex AI permission, or set ADC locally."
        )

    model_id = _normalize_model_id(model)
    text: str | None = None
    max_retries = 5
    base_delay = 1.0

    # 1. Primary Attempt using the New Google GenAI SDK Client
    try:
        client = _new_sdk_client()
        if client is not None:
            from google.genai import types

            if response_schema:

                config = types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                )

            else:

                config = types.GenerateContentConfig(
                    temperature=0.0
                )
            
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(model=model_id, contents=prompt, config=config)
                    text = getattr(response, "text", None)
                    if text is not None:
                        break
                except Exception as err:
                    if (_is_transient_error(err) or _is_quota_error(err)) and attempt < max_retries - 1:
                        delay = (base_delay * (2 ** attempt)) + random.uniform(0.1, 0.4)
                        retry_match = re.search(r"retry(?: in|Delay['\"]?:\s*['\"]?)\s*(\d+(?:\.\d+)?)s?", str(err), re.IGNORECASE)
                        if retry_match:
                            with contextlib.suppress(ValueError):
                                requested_delay = float(retry_match.group(1))
                                if requested_delay > 15.0:
                                    print(f"⚠️ Requested retry delay ({requested_delay}s) is too long. Failing fast to fallback.")
                                    raise err
                                delay = requested_delay + 1.0
                        print(f"⚠️ Primary GenAI Client experiencing high demand (503/429). Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    raise err

    except Exception as error:  # pragma: no cover - network dependent
        fallback = _handle_generation_error(error, source="GenAI SDK", prompt=prompt)
        if fallback is not None:
            return fallback

    # 2. Secondary Fallback Attempt using Legacy GenerativeAI SDK Configurations
    if text is None:
        try:
            if _configure_legacy_sdk():
                legacy_genai = _legacy_genai_module()
                legacy_model = legacy_genai.GenerativeModel(model_id)
                gen_config = {
                    "temperature": 0.0
                }

                if response_schema:
                    gen_config["response_mime_type"] = "application/json"
                    gen_config["response_schema"] = response_schema
                
                for attempt in range(max_retries):
                    try:
                        response = legacy_model.generate_content(
                            prompt,
                            generation_config=gen_config,
                            request_options={"timeout": 300.0},
                        )
                        text = getattr(response, "text", None)
                        if text is not None:
                            break
                    except Exception as err:
                        if (_is_transient_error(err) or _is_quota_error(err)) and attempt < max_retries - 1:
                            delay = (base_delay * (2 ** attempt)) + random.uniform(0.1, 0.4)
                            retry_match = re.search(r"retry(?: in|Delay['\"]?:\s*['\"]?)\s*(\d+(?:\.\d+)?)s?", str(err), re.IGNORECASE)
                            if retry_match:
                                with contextlib.suppress(ValueError):
                                    requested_delay = float(retry_match.group(1))
                                    if requested_delay > 15.0:
                                        print(f"⚠️ Requested retry delay ({requested_delay}s) is too long. Failing fast to fallback.")
                                        raise err
                                    delay = requested_delay + 1.0
                            print(f"⚠️ Legacy Gemini Client experiencing high demand (503/429). Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        raise err

        except Exception as error:  # pragma: no cover - network dependent
            fallback = _handle_generation_error(error, source="Legacy Gemini SDK", prompt=prompt)
            if fallback is not None:
                return fallback

    final_text = validate_response(text or FALLBACK_TEXT)
    set_cache(prompt, final_text)
    return final_text


LOCAL_AI_API_BASE = config.LOCAL_AI_API_BASE
LOCAL_AI_MODEL = config.LOCAL_AI_MODEL

def generate_structured_response(
    prompt: str,
    response_schema: Any
) -> dict:
    """
    Generate structured JSON using Gemini.

    Reuses generate_response() and converts the
    JSON string into a Python dictionary.
    """

    response = generate_response(
        prompt=prompt,
        response_schema=response_schema
    )

    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        return {}

    try:
        return json.loads(response)

    except Exception as e:

        print("=" * 60)
        print("STRUCTURED RESPONSE ERROR")
        print(e)
        print(response)
        print("=" * 60)

        return {}

def generate_local_response(prompt: str, model: str = LOCAL_AI_MODEL) -> str:
    """
    Calls a local LLM (like Qwen running on Ollama) to save cloud API quotas
    for tasks like re-explaining concepts or generating dynamic questions.
    """
    import requests
    try:
        print(f"🤖 [LOCAL AI] Routing request to local model {model}...")
        response = requests.post(
            LOCAL_AI_API_BASE,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=25
        )
        if response.status_code == 200:
            return response.json().get("response", "")
    except Exception as e:
        print(f"⚠️ [LOCAL AI] Request failed: {e}")
    return ""

async def stream_response(prompt: str, model: str = DEFAULT_TEXT_MODEL, response_schema: Any = None):
    text = generate_response(prompt, model=model, response_schema=response_schema)
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


def _generate_audio_sync(transcript: str, voice_name: str, language_code: str | None = None) -> bytes:
    global _tts_retry_after
    if time.monotonic() < _tts_retry_after:
        return b""

    client = _new_sdk_client()
    if client is None:
        return b""

    tts_prompt = (
        "You are Arvind Sir, an Indian Math Tutor. "
        "If the transcript is Hindi, speak it like a natural Indian Hindi teacher, not like English text. "
        f"Deliver this transcript naturally: {transcript}"
    )

    # Prefer typed config when available, fallback to plain dict.
    config: object
    try:
        from google.genai import types as genai_types  # type: ignore

        config = genai_types.GenerateContentConfig(
            temperature=0.0,
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                language_code=language_code,
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )
    except Exception:
        config = {
            "temperature": 0.0,
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "language_code": language_code,
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


async def generate_audio(transcript: str, voice_name: str = "Algenib", language_code: str | None = None) -> bytes:
    text = str(transcript or "").strip()
    if not text:
        return b""
    return await asyncio.to_thread(_generate_audio_sync, text, voice_name, language_code)