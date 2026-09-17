from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.cache.cache_manager import get_cache, set_cache
from app.core import config

GENAI_HTTP_TIMEOUT_MS = 300_000

GRADE_10_PDF_CHAPTERS = {
    "real_numbers": 1,
    "polynomials": 2,
    "pair_of_linear_equations": 3,
    "quadratic_equations": 4,
    "arithmetic_progressions": 5,
    "triangles": 6,
    "coordinate_geometry": 7,
    "introduction_to_trigonometry": 8,
    "applications_of_trigonometry": 9,
    "circles": 10,
    "constructions": 10,
    "areas_related_to_circles": 11,
    "surface_areas_and_volumes": 12,
    "statistics": 13,
    "probability": 14,
}


@lru_cache(maxsize=1)
def _google_genai_module():
    try:
        from google import genai as google_genai
    except ImportError:
        return None
    return google_genai


@lru_cache(maxsize=1)
def _legacy_genai_module():
    try:
        import google.generativeai as legacy_genai
    except ImportError:
        return None
    return legacy_genai


@dataclass(frozen=True)
class PdfExercise:
    chapter_index: int
    chapter_title: str
    exercise: str
    number: str
    prompt: str
    source_file: str
    source_file_path: str | None = None
    figure_hint: str | None = None

    def as_problem(self) -> dict[str, Any]:
        payload = {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "exercise": self.exercise,
            "number": self.number,
            "prompt": self.prompt,
            "source_file": self.source_file,
            "source": "cbse_pdf_exercise",
        }
        if self.source_file_path:
            payload["source_file_path"] = self.source_file_path
        if self.figure_hint:
            payload["figure_hint"] = self.figure_hint
        return payload


def get_pdf_chapter_number(grade: int, chapter_info: dict[str, Any], fallback: int) -> int:
    """Resolves chapter indices mapping directly to schema matrices."""
    title_slug = str(chapter_info.get("title", "")).lower().replace(" ", "_")
    return GRADE_10_PDF_CHAPTERS.get(title_slug, fallback)


def _figure_hint_from_prompt(prompt: str, chapter_title: str) -> str | None:
    text = str(prompt or "").strip()
    lowered = text.lower()
    figure_markers = ("figure", "fig.", "in fig", "in the fig", "in the figure", "given below", "as shown")
    if not any(marker in lowered for marker in figure_markers):
        return None

    labels = []
    for token in re.findall(r"\b[A-Z]{1,4}\b", text):
        if token in {"NCERT", "CBSE"}:
            continue
        if token not in labels:
            labels.append(token)
        if len(labels) >= 8:
            break

    chapter_l = str(chapter_title or "").lower()
    if "triangle" in chapter_l or any(word in lowered for word in ("triangle", "similar", "parallel", "quadrilateral", "trapezium")):
        label_text = ", ".join(labels) if labels else "the points named in the problem"
        return f"Reconstruct the figure from the problem statement. Draw the geometry for labels {label_text}; mark any parallel sides, equal angles, or proportional sides mentioned."

    if "circle" in chapter_l or "circle" in lowered:
        label_text = ", ".join(labels) if labels else "the marked points"
        return f"Reconstruct the circle figure from the problem statement. Draw the circle and label {label_text}; mark radii, chords, tangents, and given points."

    return "Reconstruct the figure described in the problem statement and label all visible points from the question."


def load_chapter_pdf_exercises(
    grade: int,
    chapter_index: int,
    chapter_title: str,
) -> list[dict[str, Any]]:
    from app.tutor_brain.curriculum import get_grade_curriculum

    curriculum = get_grade_curriculum(grade)
    chapter = next(
        (
            item
            for item in curriculum.get("chapters", [])
            if str(item.get("title", "")).strip().lower() == str(chapter_title).strip().lower()
            or str(item.get("number", "")) == str(chapter_index)
        ),
        None,
    )
    if not chapter:
        return []

    package = curriculum.get("knowledge_package") or {}
    exercises: list[dict[str, Any]] = []
    for exercise in package.get("exercises") or []:
        if not isinstance(exercise, dict):
            continue
        for question in exercise.get("questions") or []:
            if not isinstance(question, dict) or not str(question.get("question") or "").strip():
                continue
            prompt = str(question["question"]).strip()
            problem = {
                "chapter_index": chapter_index,
                "chapter_title": chapter_title,
                "exercise": f"Exercise {exercise.get('number') or exercise.get('id') or 'Practice'}",
                "number": str(question.get("number") or ""),
                "prompt": prompt,
                "source_file": "knowledge_factory",
                "source": "knowledge_factory",
            }
            figure_hint = _figure_hint_from_prompt(prompt, chapter_title)
            if figure_hint:
                problem["figure_hint"] = figure_hint
            exercises.append(problem)

    return exercises


def load_chapter_pdf_theory(grade: int, chapter_index: int, chapter_title: str = "") -> str:
    from app.tutor_brain.curriculum import get_grade_curriculum

    curriculum = get_grade_curriculum(grade)
    chapter = next(
        (
            item
            for item in curriculum.get("chapters", [])
            if str(item.get("title", "")).strip().lower() == str(chapter_title).strip().lower()
            or str(item.get("number", "")) == str(chapter_index)
        ),
        None,
    )
    if not chapter:
        return ""

    package = curriculum.get("knowledge_package") or {}
    chapter_number = str(chapter.get("number") or chapter_index)
    concepts = [
        item
        for item in package.get("concepts") or []
        if isinstance(item, dict)
        and str(item.get("section_number") or "").startswith(chapter_number)
    ]
    return "\n\n".join(
        str(item.get("name") or "").strip()
        for item in concepts
        if str(item.get("name") or "").strip()
    )


def load_all_pdf_exercises(grade: int, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for fallback_index, chapter in enumerate(chapters, start=1):
        title = str(chapter.get("title") or f"Chapter {fallback_index}")
        chapter_index = get_pdf_chapter_number(grade, chapter, fallback_index)
        if chapter_index <= 0:
            continue
        problems.extend(load_chapter_pdf_exercises(grade, chapter_index, title))
    return problems


def _focused_prompt(problem: dict[str, Any]) -> str:
    prompt = str(problem.get("prompt") or "").strip()
    number = str(problem.get("number") or "").strip().lower()
    if not prompt:
        return prompt

    roman_match = re.search(r"\(([ivx]+)\)$", number)
    target_roman = roman_match.group(1) if roman_match else ""
    if not target_roman:
        return prompt

    markers = list(re.finditer(r"\(\s*(i{1,3}|iv|v|vi{0,3}|ix|x)\s*\)", prompt, flags=re.IGNORECASE))
    if not markers:
        return prompt

    target_index = -1
    for idx, marker in enumerate(markers):
        if marker.group(1).strip().lower() == target_roman:
            target_index = idx
            break
    if target_index < 0:
        return prompt

    stem = prompt[: markers[0].start()].strip(" :-")
    start = markers[target_index].end()
    end = markers[target_index + 1].start() if target_index + 1 < len(markers) else len(prompt)
    sub = prompt[start:end].strip(" .;:")
    if not sub:
        return prompt
    return f"{stem} ({target_roman}) {sub}" if stem else f"({target_roman}) {sub}"


def _extract_figure_base64(pdf_path: str, prompt: str) -> str | None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None
        
    match = re.search(r'(?i)(?:fig\.|figure)\s*(\d+\.\d+)', prompt)
    if not match:
        return None
        
    fig_num = match.group(1)
    
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_instances = page.search_for(fig_num)
            for rect in text_instances:
                nearby_text = page.get_textbox(fitz.Rect(max(0, rect.x0 - 50), max(0, rect.y0 - 20), min(page.rect.width, rect.x1 + 50), min(page.rect.height, rect.y1 + 20)))
                if "fig" in nearby_text.lower() or "figure" in nearby_text.lower():
                    crop_rect = fitz.Rect(max(0, rect.x0 - 250), max(0, rect.y0 - 300), min(page.rect.width, rect.x1 + 250), min(page.rect.height, rect.y1 + 20))
                    pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")
                    return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        print(f"Error extracting figure base64 for {fig_num}: {e}")
        
    return None


def build_exercise_solution(
    problem: dict[str, Any],
    session_id: str | None = None,
    current_chapter: str | None = None,
) -> dict[str, Any]:
    """Builds an exercise solution payload routing directly to active LLM endpoints."""
    if current_chapter and str(current_chapter).strip():
        problem = {**problem, "chapter_title": current_chapter}
    
    prompt = _focused_prompt(problem)
    extracted_image_base64 = None
    if problem.get("source_file_path"):
        extracted_image_base64 = _extract_figure_base64(problem["source_file_path"], prompt)

    # Return static AI-free pack for Chapter 1
    if problem.get("chapter_index") == 1 or str(current_chapter).lower() == "real numbers":
        return {
            **problem,
            "steps": ["Refer to the static chapter 1 knowledge base for rule-based resolution."],
            "answer": "Static Answer Engine Engaged",
            "answer_type": "text",
        }

    # Use SymPy and rule-based logic instead of Gemini for practice
    try:
        from sympy import symbols, solve
        from app.tutor_brain.tutor_engine import clean_expression
        
        expr = clean_expression(prompt)
        x = symbols("x")
        solutions = solve(expr, x)
        
        expected = sorted([float(s.evalf()) for s in solutions if s.is_real])
        if expected:
            answer = ", ".join(str(val) for val in expected)
            steps = [
                f"Identify the equation from the prompt.",
                f"Simplify to standard form.",
                f"Solve for x using factorization or formula.",
                f"The valid roots are {answer}."
            ]
            diagram = None
        else:
            raise ValueError("No real solutions found via SymPy")
    except Exception:
        ai_solution = _build_ai_exercise_solution(
            problem, session_id=session_id, current_chapter=current_chapter, image_base64=extracted_image_base64
        )
        if ai_solution:
            steps = ai_solution.get("steps", [])
            answer = ai_solution.get("answer", "")
            diagram = ai_solution.get("diagram")
        else:
            steps = [
                "Identify and choose the matching CBSE concept from this chapter.",
                "Write the formula, theorem, or construction rule explicitly before executing equations.",
                "Substitute known numerical coordinates and variables carefully.",
                "Simplify calculation layouts sequentially to determine final answer parameters."
            ]
            answer = "Review current formula configurations to finalize problem parameters."
            diagram = None

    result = {
        **problem,
        "prompt": prompt,
        "steps": steps[:10],
        "answer": answer,
        "answer_type": "text",
    }
    
    if diagram:
        result["diagram"] = diagram
    if extracted_image_base64:
        result["image_base64"] = extracted_image_base64
            
    return result


def _build_ai_exercise_solution(
    problem: dict[str, Any],
    session_id: str | None = None,
    current_chapter: str | None = None,
    image_base64: str | None = None,
) -> dict[str, Any] | None:
    """Generate AI solution with session context to prevent cross-session contamination."""
    prompt = str(problem.get("prompt") or "").strip()
    if not prompt:
        return None

    chapter_for_solution = current_chapter or problem.get('chapter_title', '')
    session_suffix = f"|{session_id}" if session_id else ""
    img_suffix = "|img:1" if image_base64 else ""
    
    cache_key = (
        "cbse_pdf_solution_v2|"
        f"{chapter_for_solution}|{problem.get('exercise', '')}|"
        f"{problem.get('number', '')}|{prompt}{session_suffix}{img_suffix}"
    )
    
    request = f"""
Solve this CBSE Class 10 Mathematics NCERT exercise problem for a whiteboard tutor.

The attached image contains the relevant figure for this problem (if any).
If the question refers to a figure (e.g., "In Fig 10.11" or "see figure"), YOU MUST LOOK AT THE ATTACHED IMAGE to see its details (labels, angles, lengths, geometry) to solve the problem accurately.

⚠️ CRITICAL: You are solving ONLY problems from the "{chapter_for_solution}" chapter.
⚠️ Do NOT drift to concepts from other chapters like Polynomials, Real Numbers, Triangles, etc.

Chapter: {chapter_for_solution}
Exercise: {problem.get('exercise') or ''}
Question number: {problem.get('number') or ''}
Question: {prompt}

Return only valid JSON with this exact shape:
{{
  "steps": [
    "short step with the reason included",
    "next short step with the reason included"
  ],
  "answer": "final answer",
  "diagram": "optional brief diagram instructions (if a figure is needed)"
}}

Rules:
- Solve the actual question in the "{chapter_for_solution}" chapter context ONLY.
- Solve the actual question, not a similar question.
- Give 4 to 10 whiteboard steps.
- Each step must include the reason for the operation, theorem, formula, or decision.
- Use math symbols where appropriate: use `√(...)` for square roots (do NOT write the word `sqrt`), `^` for powers, `π` for pi, `×` for multiplication, `÷` for division, and `/` for fractions. Prefer Unicode math symbols (√, π, ×, ÷) rather than spelled-out words.
- If a diagram or figure is required, include a short `diagram` string in the JSON describing the figure to draw. Keep diagram instructions concise (one or two short sentences).
- Do not include markdown, code fences, greetings, commentary, or extra keys.
- Use only concepts and formulas from the {chapter_for_solution} chapter.
""".strip()

    try:
        raw = _generate_raw_json_solution(cache_key, request, image_base64)
        if not raw:
            return None
        data = _parse_json_object(raw)
        steps = [str(step).strip() for step in data.get("steps", []) if str(step).strip()]
        answer = str(data.get("answer") or "").strip()
        diagram = str(data.get("diagram") or "").strip()
        if len(steps) >= 2 and answer:
            result = {"steps": steps[:10], "answer": answer}
            if diagram:
                result["diagram"] = diagram
            result["chapter_context"] = chapter_for_solution
            return result
    except Exception as error:
        print(f"AI exercise solution failed for {chapter_for_solution}:", error)
    return None


def _generate_raw_json_solution(cache_key: str, prompt: str, image_base64: str | None = None) -> str | None:
    cached = get_cache(cache_key)
    if cached:
        return str(cached)

    text: str | None = None
    contents = []
    if image_base64:
        try:
            img_bytes = base64.b64decode(image_base64)
            google_genai = _google_genai_module()
            if google_genai is not None:
                try:
                    from google.genai import types
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                except ImportError:
                    contents.append({"mime_type": "image/png", "data": img_bytes})
        except Exception as e:
            print("Could not attach image for gemini:", e)
            
    contents.append(prompt)
    
    try:
        google_genai = _google_genai_module()
        if GEMINI_API_KEY and google_genai is not None:
            client = google_genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": GENAI_HTTP_TIMEOUT_MS})
            try:
                response = client.models.generate_content(
                    model=GEMINI_TEXT_MODEL,
                    contents=contents,
                )
                text = getattr(response, "text", None)
            except Exception as primary_error:
                print(f"Primary model {GEMINI_TEXT_MODEL} failed: {primary_error}.")
    except Exception as error:
        print("GenAI exercise solver error:", error)

    if text is None:
        try:
            legacy_genai = _legacy_genai_module()
            if GEMINI_API_KEY and legacy_genai is not None:
                legacy_genai.configure(api_key=GEMINI_API_KEY)
                model = legacy_genai.GenerativeModel(GEMINI_TEXT_MODEL)
                
                legacy_contents = []
                if image_base64:
                    try:
                        img_bytes = base64.b64decode(image_base64)
                        legacy_contents.append({"mime_type": "image/png", "data": img_bytes})
                    except Exception as e:
                        print("Could not attach image for legacy gemini:", e)
                legacy_contents.append(prompt)
                
                response = model.generate_content(legacy_contents, request_options={"timeout": 300.0})
                text = getattr(response, "text", None)
        except Exception as error:
            print("Legacy GenAI exercise solver error:", error)

    if text:
        set_cache(cache_key, text)
    return text


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    
    # Dynamically compose triple-backtick segments to prevent markdown processing breaks
    triple_backtick = "``" + "`"
    cleaned = re.sub(r"^" + triple_backtick + r"(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*" + triple_backtick + r"$", "", cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return {"steps": [], "answer": "Error parsing generated structured payload layout."}
        return {"steps": [], "answer": "Invalid json document matrix encountered."}