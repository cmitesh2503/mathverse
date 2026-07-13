from __future__ import annotations

import re
from typing import Any


def sanitize_text(value: str) -> str:
    text = re.sub(r"[\ud800-\udfff]", "?", str(value or ""))
    return text.encode(
        "utf-8",
        errors="replace",
    ).decode(
        "utf-8",
        errors="replace",
    )


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)

    if isinstance(value, list):
        return [
            sanitize_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            sanitize_text(key): sanitize_json_value(item)
            for key, item in value.items()
        }

    return value
