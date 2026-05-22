from __future__ import annotations

import json
import math
import re
from typing import Any

from .ai_gateway import generate_response
from ..cache.cache_manager import get_cache, set_cache
import time
import asyncio


PROMPT_TEMPLATE = (
    "You are a Geometry Translator.\n"
    "Input: a short textual description of a figure from a math problem (NCERT style).\n"
    "Output: a single JSON object with one key `whiteboard_actions` whose value is an array of primitive actions.\n"
    "Use only these primitive actions and properties: `draw_line` (x1,y1,x2,y2,color,thickness,label),"
    " `draw_angle` (x,y,radius,start_angle,end_angle,label,color), `write_text` (x,y,label,font_size,color),"
    " `highlight_element` (x1,y1,x2,y2,color,opacity,label).\n"
    "Do NOT output any prose. Return valid JSON only. Example:\n"
    "{\"whiteboard_actions\": [ {\"action\": \"write_text\", \"x\":10, \"y\":20, \"label\": \"What is given: a=5\"} ] }\n"
)


ALLOWED_ACTIONS = {"draw_line", "draw_angle", "write_text", "highlight_element"}


def _extract_point_labels(text: str, max_count: int = 8) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"\b[A-Z]\b", str(text or "")):
        if token in seen:
            continue
        seen.add(token)
        labels.append(token)
        if len(labels) >= max_count:
            break
    return labels


def _extract_json_like(text: str) -> dict[str, Any]:
    """Attempt to robustly extract the first JSON object from text."""
    text = text.strip()
    # Try code fence extraction
    if "```json" in text and "```" in text.split("```json")[-1]:
        try:
            block = text.split("```json")[1].split("```")[0]
            return json.loads(block)
        except Exception:
            pass
    # Try generic code fence
    if "```" in text:
        try:
            block = text.split("```\n")[1]
            return json.loads(block)
        except Exception:
            pass
    # Brute force {} extraction
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass
    # Last resort: try to parse entire string
    try:
        return json.loads(text)
    except Exception:
        raise ValueError("No JSON object found in model response")


def _validate_action(action: dict[str, Any]) -> bool:
    if not isinstance(action, dict):
        return False
    name = str(action.get("action") or "").strip()
    if name not in ALLOWED_ACTIONS:
        return False
    # Minimal required fields per action
    if name == "write_text":
        return isinstance(action.get("x"), (int, float)) and isinstance(action.get("y"), (int, float)) and isinstance(action.get("label"), str)
    if name == "draw_line":
        for k in ("x1", "y1", "x2", "y2"):
            if not isinstance(action.get(k), (int, float)):
                return False
        return True
    if name == "draw_angle":
        for k in ("x", "y", "radius", "start_angle", "end_angle"):
            if not isinstance(action.get(k), (int, float)):
                return False
        return True
    if name == "highlight_element":
        for k in ("x1", "y1", "x2", "y2"):
            if not isinstance(action.get(k), (int, float)):
                return False
        return bool(action.get("color"))
    return False


def validate_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        raise ValueError("whiteboard_actions must be a list")
    out: list[dict[str, Any]] = []
    for action in actions:
        if _validate_action(action):
            out.append(action)
        else:
            raise ValueError(f"Invalid action: {action}")
    return out


def _add_vertex_marker(x: int, y: int, label: str) -> list[dict[str, Any]]:
    return [
        {"action": "highlight_element", "x1": x - 4, "y1": y - 4, "x2": x + 4, "y2": y + 4, "color": "black", "opacity": 1.0},
        {"action": "write_text", "x": x + 6, "y": y - 6, "label": label},
    ]


def _add_axis_ticks(x1: int, y1: int, x2: int, y2: int, spacing: int = 40) -> list[dict[str, Any]]:
    ticks: list[dict[str, Any]] = []
    # horizontal ticks along x-axis
    if y1 == y2:
        start = min(x1, x2)
        end = max(x1, x2)
        for px in range(start + spacing, end, spacing):
            ticks.append({"action": "draw_line", "x1": px, "y1": y1 - 4, "x2": px, "y2": y1 + 4, "color": "black"})
    # vertical ticks along y-axis
    if x1 == x2:
        start = min(y1, y2)
        end = max(y1, y2)
        for py in range(start + spacing, end, spacing):
            ticks.append({"action": "draw_line", "x1": x1 - 4, "y1": py, "x2": x1 + 4, "y2": py, "color": "black"})
    return ticks


def _circle_polyline(cx: int, cy: int, radius: int, segments: int = 28) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pts: list[tuple[int, int]] = []
    for i in range(segments + 1):
        theta = 2.0 * math.pi * i / segments
        x = int(round(cx + radius * math.cos(theta)))
        y = int(round(cy + radius * math.sin(theta)))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        out.append({"action": "draw_line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": "violet", "thickness": 2})
    return out


def _has_drawable_primitives(actions: list[dict[str, Any]]) -> bool:
    return any(
        str(item.get("action") or "").strip().lower() in {"draw_line", "draw_angle", "highlight_element"}
        for item in actions
        if isinstance(item, dict)
    )


def _heuristic_fallback(diagram_text: str) -> list[dict[str, Any]]:
    """Return a small set of primitive actions for common keywords as a fallback."""
    t = (diagram_text or "").lower()
    if "circle" in t and ("tangent" in t or "external point" in t or "chord" in t):
        point_labels = _extract_point_labels(diagram_text, max_count=4)
        labels = point_labels[:4] if len(point_labels) >= 4 else ["O", "A", "P", "Q"]
        O_label, A_label, P_label, Q_label = labels[0], labels[1], labels[2], labels[3]

        O = (110, 90)
        A = (190, 90)
        r = 38
        theta = math.radians(42)
        P = (int(round(O[0] + r * math.cos(theta))), int(round(O[1] - r * math.sin(theta))))
        Q = (int(round(O[0] + r * math.cos(theta))), int(round(O[1] + r * math.sin(theta))))

        out: list[dict[str, Any]] = []
        out.extend(_circle_polyline(O[0], O[1], r, segments=30))
        out.extend(
            [
                {"action": "draw_line", "x1": A[0], "y1": A[1], "x2": P[0], "y2": P[1], "color": "skyblue", "thickness": 2, "label": f"{A_label}{P_label}"},
                {"action": "draw_line", "x1": A[0], "y1": A[1], "x2": Q[0], "y2": Q[1], "color": "skyblue", "thickness": 2, "label": f"{A_label}{Q_label}"},
                {"action": "draw_line", "x1": O[0], "y1": O[1], "x2": A[0], "y2": A[1], "color": "green", "thickness": 2, "label": f"{O_label}{A_label}"},
                {"action": "draw_line", "x1": O[0], "y1": O[1], "x2": P[0], "y2": P[1], "color": "green", "thickness": 2, "label": f"{O_label}{P_label}"},
                {"action": "draw_line", "x1": O[0], "y1": O[1], "x2": Q[0], "y2": Q[1], "color": "green", "thickness": 2, "label": f"{O_label}{Q_label}"},
                {"action": "draw_line", "x1": P[0], "y1": P[1], "x2": Q[0], "y2": Q[1], "color": "orange", "thickness": 2, "label": f"{P_label}{Q_label}"},
            ]
        )
        out.extend(_add_vertex_marker(O[0], O[1], O_label))
        out.extend(_add_vertex_marker(A[0], A[1], A_label))
        out.extend(_add_vertex_marker(P[0], P[1], P_label))
        out.extend(_add_vertex_marker(Q[0], Q[1], Q_label))
        return out
    if "triangle" in t:
        point_labels = _extract_point_labels(diagram_text, max_count=3)
        labels = point_labels[:3] if len(point_labels) >= 3 else ["A", "B", "C"]
        a_label, b_label, c_label = labels[0], labels[1], labels[2]
        A = (80, 60)
        B = (160, 60)
        C = (120, 120)
        out = [
            {"action": "draw_line", "x1": A[0], "y1": A[1], "x2": B[0], "y2": B[1], "label": f"{a_label}{b_label}"},
            {"action": "draw_line", "x1": B[0], "y1": B[1], "x2": C[0], "y2": C[1], "label": f"{b_label}{c_label}"},
            {"action": "draw_line", "x1": C[0], "y1": C[1], "x2": A[0], "y2": A[1], "label": f"{c_label}{a_label}"},
        ]
        out.extend(_add_vertex_marker(A[0], A[1], a_label))
        out.extend(_add_vertex_marker(B[0], B[1], b_label))
        out.extend(_add_vertex_marker(C[0], C[1], c_label))
        return out
    if "parabola" in t or "x^2" in t or "y =" in t and "x^2" in t:
        pts = []
        cx, cy = 120, 140
        width, height = 100, 60
        for i in range(21):
            tt = -1 + 2.0 * i / 20
            x = int(cx + tt * width)
            y = int(cy - height * (tt ** 2))
            pts.append((x, y))
        segs = []
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            segs.append({"action": "draw_line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        # vertex marker at middle
        vx, vy = pts[len(pts) // 2]
        segs.extend(_add_vertex_marker(vx, vy, "V"))
        # approximate focus marker above vertex
        segs.extend(_add_vertex_marker(vx, vy - 20, "F"))
        segs.append({"action": "write_text", "x": cx + width, "y": cy - height - 10, "label": "y = ax^2 + bx + c"})
        return segs
    # default: echo the description as a text label
    return [{"action": "write_text", "x": 20, "y": 140, "label": diagram_text}]


def translate_diagram_to_primitives(diagram_text: str, model: str | None = None, max_attempts: int = 1) -> list[dict[str, Any]]:
    """Translate a diagram description into primitive whiteboard actions using the LLM.

    Returns a list of validated primitive actions. On failure, returns a heuristic fallback.
    """
    # caching key
    key = "geom:v2:" + (diagram_text or "").strip().lower()
    cached = get_cache(key) if model is None else None
    if cached and isinstance(cached, list):
        if _has_drawable_primitives(cached):
            return cached
        upgraded = _heuristic_fallback(diagram_text)
        set_cache(key, upgraded)
        return upgraded
    if cached:
        return cached

    prompt = PROMPT_TEMPLATE + "\nDIAGRAM DESCRIPTION:\n" + (diagram_text or "")
    last_err = None
    for attempt in range(max_attempts):
        try:
            raw = generate_response(prompt, model=model) if model is not None else generate_response(prompt)
            parsed = _extract_json_like(raw)
            actions = parsed.get("whiteboard_actions") or []
            validated = validate_actions(actions)
            if not _has_drawable_primitives(validated):
                validated = _heuristic_fallback(diagram_text)
            set_cache(key, validated)
            return validated
        except Exception as err:
            last_err = err
            time.sleep(0.5 * (2 ** attempt))
            continue

    # final fallback
    try:
        fallback = _heuristic_fallback(diagram_text)
        set_cache(key, fallback)
        return fallback
    except Exception:
        return [{"action": "write_text", "x": 20, "y": 140, "label": "[diagram not available]"}]


async def translate_diagram_to_primitives_async(diagram_text: str, model: str | None = None, max_attempts: int = 3, backoff_base: float = 0.5) -> list[dict[str, Any]]:
    key = "geom:v2:" + (diagram_text or "").strip().lower()
    cached = get_cache(key) if model is None else None
    if cached and isinstance(cached, list):
        if _has_drawable_primitives(cached):
            return cached
        upgraded = _heuristic_fallback(diagram_text)
        set_cache(key, upgraded)
        return upgraded
    if cached:
        return cached

    prompt = PROMPT_TEMPLATE + "\nDIAGRAM DESCRIPTION:\n" + (diagram_text or "")
    last_err = None
    for attempt in range(max_attempts):
        try:
            if model is not None:
                raw = await asyncio.to_thread(generate_response, prompt, model)
            else:
                raw = await asyncio.to_thread(generate_response, prompt)
            parsed = _extract_json_like(raw)
            actions = parsed.get("whiteboard_actions") or []
            validated = validate_actions(actions)
            if not _has_drawable_primitives(validated):
                validated = _heuristic_fallback(diagram_text)
            set_cache(key, validated)
            return validated
        except Exception as err:
            last_err = err
            await asyncio.sleep(backoff_base * (2 ** attempt))
            continue

    fallback = _heuristic_fallback(diagram_text)
    set_cache(key, fallback)
    return fallback
