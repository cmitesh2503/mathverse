from __future__ import annotations

import json
import math
import re
from typing import Any

from ..cache.cache_manager import get_cache, set_cache
from .ai_gateway import generate_response


PLAN_CACHE_VERSION = "math_teaching_plan_v1"


SEMANTIC_TYPES = {
    "circle",
    "point",
    "radius",
    "diameter",
    "tangent",
    "perpendicular_marker",
    "right_angle",
    "angle",
    "parallel_lines",
    "triangle",
    "line_segment",
    "coordinate_axes",
    "graph",
    "table",
    "number_line",
}


def _json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    candidates = [cleaned]

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        extracted = cleaned[start : end + 1]
        candidates.append(extracted)
        candidates.append(_repair_json_text(extracted))

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return parsed if isinstance(parsed, dict) else {}

    return {}


def _repair_json_text(text: str) -> str:
    repaired = str(text or "").strip()
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = re.sub(r'([}\]"]) *\n\s*("[A-Za-z_][A-Za-z0-9_ -]*"\s*:)', r"\1,\n\2", repaired)
    repaired = re.sub(r"([}\]])\s*\n\s*({)", r"\1,\n\2", repaired)
    return repaired


def _normalize_object(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    obj = dict(raw)
    obj_type = str(obj.get("type") or obj.get("kind") or "").strip().lower().replace("-", "_")
    if obj_type == "perpendicular":
        obj_type = "perpendicular_marker"
    if obj_type not in SEMANTIC_TYPES:
        return None
    obj["type"] = obj_type
    return obj


def _normalize_plan(raw: dict[str, Any]) -> dict[str, Any]:
    diagram = raw.get("diagram") if isinstance(raw.get("diagram"), dict) else {}
    objects = [_normalize_object(item) for item in diagram.get("objects", []) if isinstance(diagram, dict)]
    objects = [item for item in objects if item]
    return {
        "problem_type": str(raw.get("problem_type") or "general_math").strip() or "general_math",
        "given": [str(item).strip() for item in raw.get("given", []) if str(item).strip()] if isinstance(raw.get("given"), list) else [],
        "to_find": str(raw.get("to_find") or "").strip(),
        "theorem": str(raw.get("theorem") or raw.get("concept") or "").strip(),
        "diagram": {"objects": objects},
        "solution_steps": [str(item).strip() for item in raw.get("solution_steps", []) if str(item).strip()] if isinstance(raw.get("solution_steps"), list) else [],
        "answer": str(raw.get("answer") or "").strip(),
    }


def _objects(plan: dict[str, Any]) -> list[dict[str, Any]]:
    diagram = plan.get("diagram") if isinstance(plan.get("diagram"), dict) else {}
    objects = diagram.get("objects") if isinstance(diagram, dict) else []
    return [obj for obj in objects if isinstance(obj, dict)]


def validate_math_teaching_plan(plan: dict[str, Any], *, prompt: str, steps: list[str]) -> list[str]:
    text = " ".join([prompt, *steps]).lower()
    objects = _objects(plan)
    types = [str(obj.get("type") or "").lower() for obj in objects]
    issues: list[str] = []

    if "tangent" in text and "tangent" not in types:
        issues.append("Diagram must include at least one tangent object.")
    if "perpendicular" in text and not any(t in {"right_angle", "perpendicular_marker"} for t in types):
        issues.append("Diagram must include a right_angle or perpendicular_marker object.")
    if "parallel tangent" in text or "parallel tangents" in text:
        tangent_count = sum(1 for item in types if item == "tangent")
        if tangent_count < 2:
            issues.append("Parallel tangent problems require at least two tangent objects.")
        if "parallel_lines" not in types:
            issues.append("Parallel tangent problems require a parallel_lines object.")

    triangle_labels = re.findall(r"\btriangle\s+([A-Z]{3})\b", " ".join([prompt, *steps]), flags=re.IGNORECASE)
    if triangle_labels:
        labels = set(triangle_labels[0].upper())
        has_triangle = any(obj.get("type") == "triangle" and labels.issubset(set("".join(map(str, obj.get("points", []))).upper())) for obj in objects)
        if not has_triangle:
            point_labels = {str(obj.get("label") or obj.get("name") or "").upper() for obj in objects if obj.get("type") == "point"}
            line_count = sum(1 for obj in objects if obj.get("type") in {"line_segment", "radius", "diameter"})
            if not labels.issubset(point_labels) or line_count < 3:
                issues.append(f"Triangle {''.join(sorted(labels))} must include its three points and three sides.")

    return issues


def _planner_prompt(
    *,
    prompt: str,
    solved_steps: list[str],
    answer: str,
    grade: int | None,
    exam: str | None,
    chapter: str | None,
    teaching_language: str | None,
) -> str:
    return f"""
You are a PhD-level mathematics teaching planner for Grades 8 to 12.
Turn the problem into a structured teaching object for a deterministic whiteboard renderer.

Context:
- grade: {grade or ""}
- board/exam: {exam or ""}
- chapter/topic: {chapter or ""}
- teaching_language: {teaching_language or "en-IN"}

Problem:
{prompt}

Current solved steps:
{json.dumps(solved_steps, ensure_ascii=False)}

Expected answer:
{answer}

Return only valid JSON with this shape:
{{
  "problem_type": "short stable identifier",
  "given": ["facts explicitly given or needed"],
  "to_find": "what the student must find",
  "theorem": "required theorem/concept, grade appropriate",
  "diagram": {{
    "objects": [
      {{"type": "circle", "center": "O"}},
      {{"type": "point", "label": "P", "on": "circle"}},
      {{"type": "diameter", "points": ["P", "Q"], "through": "O"}},
      {{"type": "radius", "from": "O", "to": "P"}},
      {{"type": "tangent", "at": "P", "label": "t1"}},
      {{"type": "right_angle", "at": "P", "between": ["OP", "t1"]}},
      {{"type": "parallel_lines", "lines": ["t1", "t2"]}},
      {{"type": "triangle", "points": ["A", "B", "C"]}},
      {{"type": "coordinate_axes"}},
      {{"type": "number_line"}}
    ]
  }},
  "solution_steps": ["grade appropriate board step"],
  "answer": "final answer"
}}

Rules:
- Use semantic objects, not drawing coordinates.
- If the solution mentions a tangent, include tangent object(s).
- If the solution mentions perpendicular or 90 degrees, include right_angle/perpendicular_marker object(s).
- If the problem asks for parallel tangents, include two tangent objects at opposite ends of a diameter and a parallel_lines object.
- If a named triangle is needed, include a triangle object with named points.
- Keep steps suitable for the grade, but mathematically rigorous.
- Do not output markdown or prose outside JSON.
""".strip()


def _repair_prompt(plan: dict[str, Any], issues: list[str]) -> str:
    return f"""
Repair only the diagram JSON in this math teaching plan.
Validation issues:
{json.dumps(issues, ensure_ascii=False)}

Current plan:
{json.dumps(plan, ensure_ascii=False)}

Return the full corrected plan as valid JSON only. Keep semantic objects. Do not include coordinates.
""".strip()


def _fallback_plan(prompt: str, solved_steps: list[str], answer: str) -> dict[str, Any]:
    text = " ".join([prompt, *solved_steps]).lower()
    objects: list[dict[str, Any]] = []
    theorem = ""

    if "circle" in text:
        objects.append({"type": "circle", "center": "O"})
    if "parallel tangent" in text or "parallel tangents" in text or ("diameter" in text and "tangent" in text and "perpendicular" in text):
        theorem = "Tangents at the endpoints of a diameter are parallel because each is perpendicular to the same diameter."
        objects.extend(
            [
                {"type": "diameter", "points": ["P", "Q"], "through": "O"},
                {"type": "tangent", "at": "P", "label": "t1"},
                {"type": "tangent", "at": "Q", "label": "t2"},
                {"type": "right_angle", "at": "P", "between": ["OP", "t1"]},
                {"type": "right_angle", "at": "Q", "between": ["OQ", "t2"]},
                {"type": "parallel_lines", "lines": ["t1", "t2"]},
            ]
        )
    elif "tangent" in text and ("how many" in text or "infinitely many" in text or "can a circle have" in text):
        theorem = "At every point on a circle, exactly one tangent can be drawn."
        objects.extend(
            [
                {"type": "point", "label": "P", "on": "circle"},
                {"type": "point", "label": "Q", "on": "circle"},
                {"type": "point", "label": "R", "on": "circle"},
                {"type": "tangent", "at": "P", "label": "t1"},
                {"type": "tangent", "at": "Q", "label": "t2"},
                {"type": "tangent", "at": "R", "label": "t3"},
            ]
        )
    elif "tangent" in text:
        theorem = "The tangent at any point of a circle is perpendicular to the radius through the point of contact."
        objects.extend(
            [
                {"type": "point", "label": "A"},
                {"type": "point", "label": "B", "on": "circle"},
                {"type": "radius", "from": "O", "to": "B"},
                {"type": "tangent", "at": "B", "label": "AB"},
                {"type": "right_angle", "at": "B", "between": ["OB", "AB"]},
            ]
        )

    tri = re.search(r"\btriangle\s+([A-Z]{3})\b", " ".join([prompt, *solved_steps]), flags=re.IGNORECASE)
    if tri:
        objects.append({"type": "triangle", "points": list(tri.group(1).upper())})

    return {
        "problem_type": "fallback_structured_math",
        "given": [],
        "to_find": "",
        "theorem": theorem,
        "diagram": {"objects": objects},
        "solution_steps": solved_steps,
        "answer": answer,
    }


def build_math_teaching_plan(
    *,
    prompt: str,
    solved_steps: list[str],
    answer: str = "",
    grade: int | None = None,
    exam: str | None = None,
    chapter: str | None = None,
    teaching_language: str | None = None,
) -> dict[str, Any]:
    normalized_steps = [str(step).strip() for step in solved_steps if str(step).strip()]
    key_payload = {
        "prompt": prompt,
        "steps": normalized_steps,
        "answer": answer,
        "grade": grade,
        "exam": exam,
        "chapter": chapter,
        "language": teaching_language,
    }
    cache_key = f"{PLAN_CACHE_VERSION}|{json.dumps(key_payload, sort_keys=True, ensure_ascii=False)}"
    cached = get_cache(cache_key)
    if isinstance(cached, dict):
        return cached
    if isinstance(cached, str):
        with_context = _json_object(cached)
        if with_context:
            return _normalize_plan(with_context)

    prompt_text = _planner_prompt(
        prompt=prompt,
        solved_steps=normalized_steps,
        answer=answer,
        grade=grade,
        exam=exam,
        chapter=chapter,
        teaching_language=teaching_language,
    )
    plan: dict[str, Any] | None = None
    try:
        raw = generate_response(prompt_text)
        parsed = _json_object(raw)
        plan = _normalize_plan(parsed)
        issues = validate_math_teaching_plan(plan, prompt=prompt, steps=normalized_steps)
        if issues:
            repaired = generate_response(_repair_prompt(plan, issues))
            repaired_plan = _normalize_plan(_json_object(repaired))
            if not validate_math_teaching_plan(repaired_plan, prompt=prompt, steps=normalized_steps):
                plan = repaired_plan
    except Exception as error:
        print("Math teaching planner error:", error)

    if not plan or not _objects(plan):
        plan = _fallback_plan(prompt, normalized_steps, answer)

    set_cache(cache_key, plan)
    return plan


def _action(action: str, **kwargs: Any) -> dict[str, Any]:
    payload = {"action": action, **kwargs}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["diagram"] = True
    payload["metadata"] = metadata
    return payload


def _right_angle_marker(x: int, y: int, orientation: str = "left") -> list[dict[str, Any]]:
    if orientation == "right":
        return [
            _action("draw_line", x1=x, y1=y, x2=x - 10, y2=y, color="yellow", thickness=2),
            _action("draw_line", x1=x - 10, y1=y, x2=x - 10, y2=y - 10, color="yellow", thickness=2),
            _action("draw_line", x1=x - 10, y1=y - 10, x2=x, y2=y - 10, color="yellow", thickness=2, label="90°"),
        ]
    return [
        _action("draw_line", x1=x, y1=y, x2=x + 10, y2=y, color="yellow", thickness=2),
        _action("draw_line", x1=x + 10, y1=y, x2=x + 10, y2=y - 10, color="yellow", thickness=2),
        _action("draw_line", x1=x + 10, y1=y - 10, x2=x, y2=y - 10, color="yellow", thickness=2, label="90°"),
    ]


def _point_on_circle(cx: int, cy: int, radius: int, angle_deg: float) -> tuple[int, int]:
    radians = math.radians(angle_deg)
    return int(round(cx + radius * math.cos(radians))), int(round(cy + radius * math.sin(radians)))


def render_math_plan_diagram(plan: dict[str, Any]) -> list[dict[str, Any]]:
    objects = _objects(plan)
    if not objects:
        return []

    types = [str(obj.get("type") or "") for obj in objects]
    cx, cy, radius = 120, 92, 46
    actions: list[dict[str, Any]] = []

    if "circle" in types:
        actions.append(_action("draw_circle", x=cx, y=cy, radius=radius, color="violet", thickness=3, label="circle"))
        actions.append(_action("write_text", x=cx - 4, y=cy + 4, label="O"))

    tangent_objects = [obj for obj in objects if obj.get("type") == "tangent"]
    has_parallel = any(obj.get("type") == "parallel_lines" for obj in objects)
    has_diameter = any(obj.get("type") == "diameter" for obj in objects)

    if has_parallel and len(tangent_objects) >= 2:
        left = (cx - radius, cy)
        right = (cx + radius, cy)
        actions.append(_action("draw_line", x1=left[0], y1=left[1], x2=right[0], y2=right[1], color="green", thickness=3, label="diameter PQ"))
        actions.append(_action("draw_line", x1=left[0], y1=cy - 64, x2=left[0], y2=cy + 64, color="skyblue", thickness=3, label=str(tangent_objects[0].get("label") or "t1")))
        actions.append(_action("draw_line", x1=right[0], y1=cy - 64, x2=right[0], y2=cy + 64, color="skyblue", thickness=3, label=str(tangent_objects[1].get("label") or "t2")))
        actions.extend(_right_angle_marker(left[0], left[1], "left"))
        actions.extend(_right_angle_marker(right[0], right[1], "right"))
        actions.append(_action("write_text", x=left[0] - 14, y=left[1] + 2, label="P"))
        actions.append(_action("write_text", x=right[0] + 4, y=right[1] + 2, label="Q"))
        actions.append(_action("write_text", x=right[0] + 18, y=cy - 38, label=f"{tangent_objects[0].get('label') or 't1'} || {tangent_objects[1].get('label') or 't2'}"))
        return actions

    if len(tangent_objects) >= 3:
        angles = [-90, 0, 45, 135]
        for index, tangent in enumerate(tangent_objects[:4]):
            px, py = _point_on_circle(cx, cy, radius, angles[index])
            label = str(tangent.get("label") or f"t{index + 1}")
            if angles[index] in {-90, 90}:
                actions.append(_action("draw_line", x1=px - 58, y1=py, x2=px + 58, y2=py, color="skyblue", thickness=2, label=label))
            elif angles[index] == 0:
                actions.append(_action("draw_line", x1=px, y1=py - 58, x2=px, y2=py + 58, color="orange", thickness=2, label=label))
            else:
                actions.append(_action("draw_line", x1=px - 42, y1=py + 42, x2=px + 42, y2=py - 42, color="green", thickness=2, label=label))
        actions.append(_action("write_text", x=cx + radius + 22, y=cy - 50, label="one tangent at each point"))
        return actions

    if tangent_objects:
        contact = tangent_objects[0].get("at") or "B"
        contact_label = str(contact)
        bx, by = cx + radius, cy
        ax, ay = bx, cy - 64
        actions.append(_action("draw_line", x1=cx, y1=cy, x2=bx, y2=by, color="green", thickness=3, label=f"O{contact_label}"))
        actions.append(_action("draw_line", x1=bx, y1=by, x2=ax, y2=ay, color="skyblue", thickness=3, label=str(tangent_objects[0].get("label") or f"A{contact_label}")))
        actions.append(_action("draw_line", x1=cx, y1=cy, x2=ax, y2=ay, color="orange", thickness=3, label="OA"))
        actions.extend(_right_angle_marker(bx, by, "left"))
        actions.append(_action("write_text", x=bx + 4, y=by + 12, label=contact_label))
        actions.append(_action("write_text", x=ax + 4, y=ay, label="A"))
        return actions

    triangle = next((obj for obj in objects if obj.get("type") == "triangle"), None)
    if triangle:
        pts = [str(item) for item in triangle.get("points", ["A", "B", "C"])][:3]
        while len(pts) < 3:
            pts.append(chr(ord("A") + len(pts)))
        a, b, c = pts
        points = {a: (120, 26), b: (34, 136), c: (260, 136)}
        actions.extend(
            [
                _action("draw_line", x1=points[b][0], y1=points[b][1], x2=points[c][0], y2=points[c][1], color="skyblue", thickness=3, label=f"{b}{c}"),
                _action("draw_line", x1=points[a][0], y1=points[a][1], x2=points[b][0], y2=points[b][1], color="skyblue", thickness=3, label=f"{a}{b}"),
                _action("draw_line", x1=points[a][0], y1=points[a][1], x2=points[c][0], y2=points[c][1], color="skyblue", thickness=3, label=f"{a}{c}"),
            ]
        )
        for label, (x, y) in points.items():
            actions.append(_action("write_text", x=x, y=y - 8 if label == a else y + 14, label=label))
        return actions

    if has_diameter:
        actions.append(_action("draw_line", x1=cx - radius, y1=cy, x2=cx + radius, y2=cy, color="green", thickness=3, label="diameter"))

    return actions
