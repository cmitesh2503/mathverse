from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from .evaluation_service import build_bulk_evaluation_prompt, normalize_bulk_evaluation_payload
from .rag_service import retrieve_context

from ..core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL


MODEL_ID = GEMINI_TEXT_MODEL
GENAI_HTTP_TIMEOUT_MS = 300_000


@lru_cache(maxsize=1)
def _google_genai_module():
    try:
        from google import genai as google_genai
    except ImportError:  # pragma: no cover - optional dependency
        return None
    return google_genai


def _extract_json(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    if not content:
        return {}

    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", content)
    if fenced:
        content = fenced.group(1)

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        with_context = content[start : end + 1]
        try:
            parsed = json.loads(with_context)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}

    return {}


def evaluate_submission(
    *,
    test_id: str,
    student_id: str,
    student_name: str,
    raw_image_bytes: bytes,
    test_name: str | None = None,
    test_number: int | None = None,
) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY/GOOGLE_API_KEY is not configured.")
    google_genai = _google_genai_module()
    if google_genai is None:
        raise RuntimeError("google-genai package is required for multimodal bulk evaluation.")
    if not raw_image_bytes:
        raise ValueError("Answer-sheet image bytes are required.")

    rag_query = f"CBSE test rules for test_id={test_id}; question paper; marking scheme"
    context = retrieve_context(
        topic=rag_query,
        n_results=10,
        metadata_filter={"test_id": test_id},
    )
    prompt = build_bulk_evaluation_prompt(
        test_id=test_id,
        student_id=student_id,
        student_name=student_name,
        test_name=test_name,
        test_number=test_number,
        context=context,
    )

    client = google_genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": GENAI_HTTP_TIMEOUT_MS})
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            prompt,
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": raw_image_bytes,
                }
            },
        ],
    )

    parsed = _extract_json(getattr(response, "text", "") or "")
    return normalize_bulk_evaluation_payload(
        parsed,
        test_id=test_id,
        student_id=student_id,
        student_name=student_name,
        test_name=test_name,
        test_number=test_number,
    )
