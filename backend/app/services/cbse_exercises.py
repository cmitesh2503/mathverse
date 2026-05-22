from __future__ import annotations

import math
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.cache.cache_manager import get_cache, set_cache
from app.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover - optional dependency
    google_genai = None

try:
    import google.generativeai as legacy_genai
except ImportError:  # pragma: no cover - optional dependency
    legacy_genai = None

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover - optional at import time
    PdfReader = None


PDF_ROOT = Path(__file__).resolve().parents[1] / "data" / "pdfs"
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


@dataclass(frozen=True)
class PdfExercise:
    chapter_index: int
    chapter_title: str
    exercise: str
    number: str
    prompt: str
    source_file: str

    def as_problem(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "exercise": self.exercise,
            "number": self.number,
            "prompt": self.prompt,
            "source_file": self.source_file,
            "source": "cbse_pdf_exercise",
        }


def _pdf_dir(grade: int) -> Path:
    return PDF_ROOT / f"std_{int(grade or 10)}"


def _chapter_pdf_path(grade: int, chapter_index: int) -> Path | None:
    directory = _pdf_dir(grade)
    preferred = directory / f"class{int(grade or 10)}_maths_ch{chapter_index}.pdf"
    if preferred.exists():
        return preferred

    chapter_marker = f"ch-{chapter_index:02d}"
    for path in sorted(directory.glob("*.pdf")):
        normalized = path.name.lower().replace(" ", "")
        if chapter_marker in normalized or f"ch{chapter_index}" in normalized:
            return path
    return None


def get_pdf_chapter_number(grade: int, chapter: dict[str, Any], fallback_index: int) -> int:
    if int(grade or 10) == 10:
        slug = str(chapter.get("slug") or "")
        if slug in GRADE_10_PDF_CHAPTERS:
            return GRADE_10_PDF_CHAPTERS[slug]
    return fallback_index


def _clean_text(text: str) -> str:
    replacements = {
        "\uf0b9": "",
        "\uf0ba": "",
        "\uf0bb": "",
        "\uf0bc": "",
        "\uf0bd": "",
        "\uf0be": "",
        "\uf0b4": "",
        "": "!=",
        "": "x",
        "": "-",
        "": "+",
        "": "pi",
        "×": "x",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"Reprint\s+\d{4}-\d{2}", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*\d+\s+MATHEMA\s*TICS\s*\n", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*[A-Z][A-Z\s]{4,}\s+\d+\s*\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@lru_cache(maxsize=64)
def _extract_pdf_text(path: str) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is not installed; cannot read CBSE PDFs.")
    reader = PdfReader(path)
    return _clean_text("\n".join(page.extract_text() or "" for page in reader.pages))


def _exercise_segments(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"\bEXERCISE\s+(\d+(?:\.\d+)*)\b", text, flags=re.IGNORECASE))
    segments: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        next_section = re.search(r"\n\s*\d+\.\d+\s+[A-Z][A-Za-z]", body)
        if next_section:
            body = body[: next_section.start()]
        segments.append((match.group(1), body.strip()))
    return segments


def _split_questions(body: str) -> list[tuple[str, str]]:
    body = re.sub(r"\n+", "\n", body)
    markers = list(re.finditer(r"(?:^|\n)\s*(\d+)\.\s*", body))
    questions: list[tuple[str, str]] = []
    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(body)
        prompt = body[start:end].strip()
        prompt = re.sub(r"\s*\n\s*", " ", prompt)
        prompt = re.sub(r"\s{2,}", " ", prompt).strip(" -")
        if 12 <= len(prompt) <= 1600:
            questions.append((marker.group(1), prompt))
    return questions


def _split_subparts(prompt: str) -> list[tuple[str, str]]:
    text = str(prompt or "").strip()
    if not text:
        return []
    markers = list(re.finditer(r"\(\s*(i{1,3}|iv|v|vi{0,3}|ix|x)\s*\)", text, flags=re.IGNORECASE))
    if len(markers) < 2:
        return []
    stem = text[: markers[0].start()].strip(" :-")
    parts: list[tuple[str, str]] = []
    for idx, marker in enumerate(markers):
        start = marker.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(text)
        roman = marker.group(1).lower()
        sub = text[start:end].strip(" .;:")
        if not sub:
            continue
        combined = f"{stem} ({roman}) {sub}" if stem else f"({roman}) {sub}"
        parts.append((roman, combined))
    return parts


def load_chapter_pdf_exercises(
    grade: int,
    chapter_index: int,
    chapter_title: str,
) -> list[dict[str, Any]]:
    path = _chapter_pdf_path(grade, chapter_index)
    if path is None:
        return []

    text = _extract_pdf_text(str(path))
    exercises: list[PdfExercise] = []
    for exercise_name, body in _exercise_segments(text):
        for number, prompt in _split_questions(body):
            subparts = _split_subparts(prompt)
            if subparts:
                for roman, subprompt in subparts:
                    exercises.append(
                        PdfExercise(
                            chapter_index=chapter_index,
                            chapter_title=chapter_title,
                            exercise=f"Exercise {exercise_name}",
                            number=f"{number}({roman})",
                            prompt=subprompt,
                            source_file=path.name,
                        )
                    )
            else:
                exercises.append(
                    PdfExercise(
                        chapter_index=chapter_index,
                        chapter_title=chapter_title,
                        exercise=f"Exercise {exercise_name}",
                        number=number,
                        prompt=prompt,
                        source_file=path.name,
                    )
                )
    return [exercise.as_problem() for exercise in exercises]


def load_all_pdf_exercises(grade: int, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for fallback_index, chapter in enumerate(chapters, start=1):
        title = str(chapter.get("title") or f"Chapter {fallback_index}")
        chapter_index = get_pdf_chapter_number(grade, chapter, fallback_index)
        if chapter_index <= 0:
            continue
        problems.extend(load_chapter_pdf_exercises(grade, chapter_index, title))
    return problems


def _integers(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"(?<![\w.])-?\d+(?![\w.])", text)]


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


def _prime_factor_steps(numbers: list[int]) -> list[str]:
    steps: list[str] = []
    for number in numbers[:6]:
        n = abs(number)
        factor = 2
        factors: list[int] = []
        while factor * factor <= n:
            while n % factor == 0:
                factors.append(factor)
                n //= factor
            factor += 1 if factor == 2 else 2
        if n > 1:
            factors.append(n)
        rendered = " x ".join(str(item) for item in factors) if factors else str(number)
        steps.append(f"{number} = {rendered}")
    return steps


def _prime_factors_of(n: int) -> list[int]:
    value = abs(int(n))
    if value <= 1:
        return [value]
    out: list[int] = []
    d = 2
    while d * d <= value:
        while value % d == 0:
            out.append(d)
            value //= d
        d += 1 if d == 2 else 2
    if value > 1:
        out.append(value)
    return out


def build_exercise_solution(
    problem: dict[str, Any],
    session_id: str | None = None,
    current_chapter: str | None = None,
) -> dict[str, Any]:
    """Build exercise solution with optional session/chapter context to prevent context loss.
    
    Args:
        problem: The problem dict with prompt, chapter_title, etc.
        session_id: Optional session ID to ensure cache isolation between sessions
        current_chapter: Optional current chapter to validate and enforce context
    """
    # Enforce chapter context if provided and different from problem
    if current_chapter and str(current_chapter).strip():
        problem = {**problem, "chapter_title": current_chapter}
    
    prompt = _focused_prompt(problem)
    lowered = prompt.lower()
    numbers = _integers(prompt)
    steps: list[str]
    answer: str | None = None

    euclid_match = re.search(r"write\s+(\d+)\s+in\s+the\s+form\s+(\d+)\s*q\s*\+\s*r", lowered)
    fraction_match = re.search(r"(\d+)\s*/\s*(\d+)", lowered)

    if "euclid" in lowered and "division lemma" in lowered and euclid_match:
        dividend = int(euclid_match.group(1))
        divisor = int(euclid_match.group(2))
        quotient = dividend // divisor
        remainder = dividend % divisor
        steps = [
            "Use Euclid's division lemma: a = bq + r with 0 <= r < b.",
            f"Here a = {dividend} and b = {divisor}, so divide {dividend} by {divisor}.",
            f"Quotient is {quotient} because {divisor} x {quotient} = {divisor * quotient}.",
            f"Remainder is {remainder} because {dividend} - {divisor * quotient} = {remainder}.",
            f"So {dividend} = {divisor} x {quotient} + {remainder}.",
            f"Check remainder rule: 0 <= {remainder} < {divisor}.",
        ]
        answer = f"q = {quotient}, r = {remainder}"
    elif ("terminating decimal expansion" in lowered or "repeating decimal expansion" in lowered) and fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        common = math.gcd(abs(numerator), abs(denominator)) or 1
        reduced_den = abs(denominator) // common
        original_reduced = reduced_den
        while reduced_den % 2 == 0:
            reduced_den //= 2
        while reduced_den % 5 == 0:
            reduced_den //= 5
        terminating = reduced_den == 1
        steps = [
            f"First reduce {numerator}/{denominator} to lowest terms by dividing by HCF {common}.",
            f"Reduced denominator is {original_reduced}.",
            "A rational number has a terminating decimal iff the reduced denominator has only prime factors 2 and/or 5.",
            "Remove all factors of 2 and 5 from the reduced denominator.",
            f"Remaining factor after removing 2 and 5 is {reduced_den}.",
            "If the remaining factor is 1, decimal terminates; otherwise it repeats.",
        ]
        answer = (
            "Terminating decimal expansion"
            if terminating
            else "Non-terminating repeating decimal expansion"
        )
    elif "circular path" in lowered and "starting point" in lowered and len(numbers) >= 2:
        times = [number for number in numbers if number > 1][:2]
        if len(times) >= 2:
            first_time, second_time = times[0], times[1]
            hcf = math.gcd(first_time, second_time)
            lcm = abs(first_time * second_time) // hcf
            steps = [
                f"Sonia reaches the starting point every {first_time} minutes, because one round takes {first_time} minutes.",
                f"Ravi reaches the starting point every {second_time} minutes, because one round takes {second_time} minutes.",
                "They meet again at the starting point only at a common multiple of both times.",
                f"The least such time is LCM({first_time}, {second_time}).",
                f"HCF({first_time}, {second_time}) = {hcf}, so LCM = ({first_time} x {second_time}) / {hcf} = {lcm}.",
                f"Therefore, they meet again at the starting point after {lcm} minutes.",
            ]
            answer = f"{lcm} minutes"
        else:
            steps = [
                "List the time taken by each person for one full round.",
                "Find the LCM of those times, because both must complete whole rounds.",
                "That LCM is the first time they are together again at the starting point.",
            ]
            answer = "LCM of the round times"
    elif "composite number" in lowered or "composite numbers" in lowered:
        steps = [
            "A composite number has a factor other than 1 and itself.",
            "For 7 x 11 x 13 + 13, take 13 common because both terms contain 13.",
            "7 x 11 x 13 + 13 = 13 x (7 x 11 + 1) = 13 x 78.",
            "Since it is written as 13 x 78, it has factors other than 1 and itself, so it is composite.",
            "For 7 x 6 x 5 x 4 x 3 x 2 x 1 + 5, take 5 common because both terms contain 5.",
            "7 x 6 x 5 x 4 x 3 x 2 x 1 + 5 = 5 x (7 x 6 x 4 x 3 x 2 x 1 + 1).",
            "The bracket is 1009, so the number is 5 x 1009.",
            "Since it is written as 5 x 1009, it is composite.",
        ]
        answer = "Both numbers are composite."
    elif "given that hcf" in lowered and "lcm" in lowered and len(numbers) >= 3:
        hcf_match = re.search(r"hcf\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*(\d+)", prompt, flags=re.IGNORECASE)
        if hcf_match:
            a, b, hcf = (abs(int(hcf_match.group(i))) for i in (1, 2, 3))
        else:
            hcf = abs(numbers[0])
            a, b = abs(numbers[1]), abs(numbers[2])
        lcm = abs(a * b) // hcf if hcf else None
        steps = [
            "Use the identity for two positive integers: HCF x LCM = product of the numbers.",
            f"Given HCF = {hcf}, numbers are {a} and {b}.",
            f"LCM = ({a} x {b}) / {hcf}.",
            f"LCM = {lcm}.",
        ]
        answer = f"LCM = {lcm}"
    elif "prime factor" in lowered and numbers:
        steps = [
            "Break each number by repeatedly dividing by the smallest possible prime, because prime factorisation uses only prime numbers.",
            *_prime_factor_steps(numbers),
        ]
        answer = "Prime factorisations are written above."
    elif "lcm" in lowered and "hcf" in lowered and len(numbers) >= 2:
        pair_matches = re.findall(r"(\d+)\s*(?:,|and)\s*(\d+)", prompt, flags=re.IGNORECASE)
        pairs = [(int(a), int(b)) for a, b in pair_matches[:8]]
        if pairs:
            steps = []
            answers: list[str] = []
            for label_index, (a, b) in enumerate(pairs, start=1):
                fa = _prime_factors_of(a)
                fb = _prime_factors_of(b)
                hcf = math.gcd(a, b)
                lcm = abs(a * b) // hcf
                steps.append(f"Part {label_index}: {a} = {' x '.join(str(x) for x in fa)}")
                steps.append(f"Part {label_index}: {b} = {' x '.join(str(x) for x in fb)}")
                common = sorted(set(fa).intersection(set(fb)))
                if common:
                    common_text = ", ".join(f"[{c}]" for c in common)
                    steps.append(f"Part {label_index}: Circle common prime factors in both lines: {common_text}.")
                else:
                    steps.append(f"Part {label_index}: No common prime factor, so HCF = 1.")
                steps.append(f"Part {label_index}: HCF = {hcf}")
                steps.append(
                    f"Part {label_index}: LCM = product of highest powers of all primes = {lcm}"
                )
                steps.append(f"Part {label_index}: Check -> {hcf} x {lcm} = {hcf * lcm}, and {a} x {b} = {a * b}")
                answers.append(f"({a}, {b}): HCF {hcf}, LCM {lcm}")
            answer = "; ".join(answers)
        else:
            values = [abs(number) for number in numbers[:4] if number]
            hcf = values[0]
            lcm = values[0]
            for value in values[1:]:
                hcf = math.gcd(hcf, value)
                lcm = abs(lcm * value) // math.gcd(lcm, value)
            steps = [
                f"Numbers to compare: {', '.join(str(value) for value in values)}.",
                "Derive prime factorisation of each number first.",
                *[
                    f"{value} = {' x '.join(str(x) for x in _prime_factors_of(value))}"
                    for value in values
                ],
                "Find HCF from common prime factors with smallest powers.",
                "Find LCM from all prime factors with greatest powers.",
                f"HCF = {hcf} and LCM = {lcm}.",
            ]
            if len(values) == 2:
                steps.append(f"Check: HCF x LCM = {hcf * lcm}, product = {values[0] * values[1]}.")
            answer = f"HCF = {hcf}, LCM = {lcm}"
    elif "end with the digit 0" in lowered:
        steps = [
            "A number ending in 0 must be divisible by 10, because every such number is 10 x some integer.",
            "So its prime factorisation must contain both 2 and 5, because 10 = 2 x 5.",
            "6^n has only the prime factors 2 and 3, because 6 = 2 x 3.",
            "There is no factor 5 in 6^n for any natural number n.",
            "Therefore, 6^n cannot end with the digit 0.",
        ]
        answer = "No"
    elif "irrational" in lowered and str(problem.get("chapter_title", "")).lower() == "real numbers":
        if "following are irrationals" in lowered:
            steps = [
                "For 1 / sqrt(2), assume it is rational; then its reciprocal sqrt(2) would be rational.",
                "But sqrt(2) is irrational, so 1 / sqrt(2) is irrational.",
                "For 7sqrt(5), assume it is rational.",
                "Dividing by 7 would make sqrt(5) rational, but sqrt(5) is irrational.",
                "So 7sqrt(5) is irrational.",
                "For 6 + sqrt(2), assume it is rational.",
                "Subtracting 6 would make sqrt(2) rational, but sqrt(2) is irrational.",
                "So 6 + sqrt(2) is irrational.",
            ]
            answer = "1 / sqrt(2), 7sqrt(5), and 6 + sqrt(2) are irrational."
        elif "32 5" in lowered or "3+2" in lowered or "3 + 2" in lowered:
            steps = [
                "We prove by contradiction because irrationality proofs start by assuming the number is rational.",
                "Assume 3 + 2sqrt(5) is rational.",
                "Then 2sqrt(5) = (3 + 2sqrt(5)) - 3 is rational, because rational minus rational is rational.",
                "So sqrt(5) is rational after dividing by 2, because rational divided by non-zero rational is rational.",
                "But sqrt(5) is irrational, which contradicts the result.",
                "Therefore, 3 + 2sqrt(5) is irrational.",
            ]
            answer = "3 + 2sqrt(5) is irrational."
        elif "75" in lowered:
            steps = [
                "Read the extracted expression as 7sqrt(5), the standard NCERT item in this exercise.",
                "We prove by contradiction because the question asks for irrationality.",
                "Assume 7sqrt(5) is rational.",
                "Then sqrt(5) is rational after dividing by 7.",
                "But sqrt(5) is irrational, so the assumption is impossible.",
                "Therefore, 7sqrt(5) is irrational.",
            ]
            answer = "7sqrt(5) is irrational."
        elif "62" in lowered:
            steps = [
                "Read the extracted expression as 6 + sqrt(2), the standard NCERT item in this exercise.",
                "Assume 6 + sqrt(2) is rational.",
                "Then sqrt(2) = (6 + sqrt(2)) - 6 is rational.",
                "But sqrt(2) is irrational, which is a contradiction.",
                "Therefore, 6 + sqrt(2) is irrational.",
            ]
            answer = "6 + sqrt(2) is irrational."
        elif "1 2" in lowered:
            steps = [
                "Read the extracted expression as 1 / sqrt(2), the standard NCERT item in this exercise.",
                "Assume 1 / sqrt(2) is rational.",
                "Then its reciprocal sqrt(2) is rational, because the reciprocal of a non-zero rational is rational.",
                "But sqrt(2) is irrational, so the assumption is false.",
                "Therefore, 1 / sqrt(2) is irrational.",
            ]
            answer = "1 / sqrt(2) is irrational."
        else:
            radicand = 5 if "5" in lowered else 2
            steps = [
                f"We prove sqrt({radicand}) is irrational by contradiction.",
                f"Assume sqrt({radicand}) = a / b, where a and b are coprime positive integers.",
                f"Squaring both sides gives {radicand} = a^2 / b^2, so a^2 = {radicand}b^2.",
                f"This means {radicand} divides a^2, so {radicand} divides a.",
                f"Write a = {radicand}k and substitute back; then b is also divisible by {radicand}.",
                "Now a and b have a common factor, contradicting that they were coprime.",
                f"Therefore, sqrt({radicand}) is irrational.",
            ]
            answer = f"sqrt({radicand}) is irrational."
    else:
        ai_solution = _build_ai_exercise_solution(problem, session_id=session_id, current_chapter=current_chapter)
        if ai_solution:
            steps = ai_solution["steps"]
            answer = ai_solution["answer"]
        else:
            steps = [
                "Read the question and identify the known values.",
                "Choose the matching CBSE concept from this chapter.",
                "Write the formula, theorem, or construction rule before calculation.",
                "Substitute the known values carefully.",
                "Simplify step by step and state the final result.",
            ]
            answer = "Solution needs the chapter method shown in the steps."

    result = {
        **problem,
        "prompt": prompt,
        "steps": steps[:10],
        "answer": answer,
        "answer_type": "text",
    }
    
    # Include diagram if present in AI solution
    if "ai_solution" in locals() and ai_solution and "diagram" in ai_solution:
        result["diagram"] = ai_solution["diagram"]
    
    return result


def _build_ai_exercise_solution(
    problem: dict[str, Any],
    session_id: str | None = None,
    current_chapter: str | None = None,
) -> dict[str, Any] | None:
    """Generate AI solution with session context to prevent cross-session contamination.
    
    Args:
        problem: The problem dict
        session_id: Session ID for cache isolation
        current_chapter: Current chapter context to enforce in solution
    """
    prompt = str(problem.get("prompt") or "").strip()
    if not prompt:
        return None

    # Use current_chapter if provided to enforce context
    chapter_for_solution = current_chapter or problem.get('chapter_title', '')
    
    # CRITICAL: Include session_id in cache key to prevent cross-session contamination
    session_suffix = f"|{session_id}" if session_id else ""
    cache_key = (
        "cbse_pdf_solution_v2|"
        f"{chapter_for_solution}|{problem.get('exercise', '')}|"
        f"{problem.get('number', '')}|{prompt}{session_suffix}"
    )
    # CRITICAL: Enforce chapter context in prompt to prevent AI from drifting to wrong topics
    request = f"""
Solve this CBSE Class 10 Mathematics NCERT exercise problem for a whiteboard tutor.

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
 - Each step must include the reason for the operation, theorem, formula, or decision.
 - Use math symbols where appropriate: use `√(...)` for square roots (do NOT write the word `sqrt`), `^` for powers, `π` for pi, `×` for multiplication, `÷` for division, and `/` for fractions. Prefer Unicode math symbols (√, π, ×, ÷) rather than spelled-out words.
- If a diagram or figure is required, include a short `diagram` string in the JSON describing the figure to draw. Keep diagram instructions concise (one or two short sentences).
- Do not include markdown, code fences, greetings, commentary, or extra keys.
- Use only concepts and formulas from the {chapter_for_solution} chapter.
""".strip()

    try:
        raw = _generate_raw_json_solution(cache_key, request)
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
            # Preserve chapter context in result
            result["chapter_context"] = chapter_for_solution
            return result
    except Exception as error:
        print(f"AI exercise solution failed for {chapter_for_solution}:", error)
    return None


def _generate_raw_json_solution(cache_key: str, prompt: str) -> str | None:
    cached = get_cache(cache_key)
    if cached:
        return str(cached)

    text: str | None = None
    try:
        if GEMINI_API_KEY and google_genai is not None:
            client = google_genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
            )
            text = getattr(response, "text", None)
    except Exception as error:
        print("GenAI exercise solver error:", error)

    if text is None:
        try:
            if GEMINI_API_KEY and legacy_genai is not None:
                legacy_genai.configure(api_key=GEMINI_API_KEY)
                model = legacy_genai.GenerativeModel(GEMINI_TEXT_MODEL)
                response = model.generate_content(prompt)
                text = getattr(response, "text", None)
        except Exception as error:
            print("Legacy GenAI exercise solver error:", error)

    if text:
        set_cache(cache_key, text)
    return text


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
