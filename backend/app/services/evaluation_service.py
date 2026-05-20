from __future__ import annotations

from typing import Any

EVALUATION_SCHEMA_TEMPLATE = """
{
  "student_id": "STU_88D294",
  "student_name": "Mitesh Chokshi",
  "test_id": "cbse_math_mock_2026",
  "total_maximum_marks": 80.0,
  "total_secured_marks": 54.5,
  "percentage_secured": "68.12%",
  "concept_mastery_insights": {
    "strong_concepts": [
      "Real Numbers (Prime Factorization)",
      "Linear Equation Concept Formulations"
    ],
    "weak_concepts": [
      "Quadratic Equations Final Calculations",
      "Coordinate Geometry Axis Labels"
    ]
  },
  "detailed_answer_breakdown": [
    {
      "question_number": "Q2",
      "section": "Section B",
      "question_text": "A motor boat whose speed is 18 km/h...",
      "max_marks": 5.0,
      "allocated_marks": 3.0,
      "step_wise_credits": {
        "formula_and_given_data": 1.0,
        "step_progression_lines": 2.0,
        "final_value_and_units": 0.0
      },
      "step_by_step_audit": "Equation factorization strings were perfect. However, final notation mark was dropped due to missing 'km/h' speed limits units.",
      "remediation_advice": "Always ensure the contextual parameters match the final metric units during final reduction check lines."
    }
  ]
}
""".strip()


def build_bulk_evaluation_prompt(
    *,
    test_id: str,
    student_id: str,
    student_name: str,
    test_name: str | None,
    test_number: int | None,
    context: str,
) -> str:
    return (
        "You are Arvind Sir, a strict CBSE board evaluator. Grade ONLY using the retrieved context (question paper + marking scheme). "
        "If evidence is incomplete, be conservative and explain deductions clearly. Return JSON only. No markdown.\n\n"
        "JSON schema to follow exactly:\n"
        f"{EVALUATION_SCHEMA_TEMPLATE}\n\n"
        f"student_id: {student_id}\n"
        f"student_name: {student_name}\n"
        f"test_id: {test_id}\n"
        f"test_name: {test_name or ''}\n"
        f"test_number: {test_number if test_number is not None else ''}\n\n"
        "Retrieved context:\n"
        f"{context or 'No vector context found.'}"
    )


def normalize_bulk_evaluation_payload(
    parsed: dict[str, Any],
    *,
    test_id: str,
    student_id: str,
    student_name: str,
    test_name: str | None,
    test_number: int | None,
) -> dict[str, Any]:
    total_maximum = float(parsed.get("total_maximum_marks", 0) or 0)
    total_secured = float(parsed.get("total_secured_marks", 0) or 0)

    raw_insights = parsed.get("concept_mastery_insights") if isinstance(parsed.get("concept_mastery_insights"), dict) else {}
    strong = raw_insights.get("strong_concepts") if isinstance(raw_insights, dict) else []
    weak = raw_insights.get("weak_concepts") if isinstance(raw_insights, dict) else []
    strong_concepts = [str(item).strip() for item in strong if str(item).strip()] if isinstance(strong, list) else []
    weak_concepts = [str(item).strip() for item in weak if str(item).strip()] if isinstance(weak, list) else []

    normalized_breakdown: list[dict[str, Any]] = []
    raw_breakdown = parsed.get("detailed_answer_breakdown")
    if isinstance(raw_breakdown, list):
        for item in raw_breakdown:
            if not isinstance(item, dict):
                continue

            step_raw = item.get("step_wise_credits") if isinstance(item.get("step_wise_credits"), dict) else {}
            normalized_breakdown.append(
                {
                    "question_number": str(item.get("question_number", "")).strip(),
                    "section": str(item.get("section", "")).strip(),
                    "question_text": str(item.get("question_text", "")).strip(),
                    "max_marks": float(item.get("max_marks", 0) or 0),
                    "allocated_marks": float(item.get("allocated_marks", 0) or 0),
                    "step_wise_credits": {
                        "formula_and_given_data": float(step_raw.get("formula_and_given_data", 0) or 0),
                        "step_progression_lines": float(step_raw.get("step_progression_lines", 0) or 0),
                        "final_value_and_units": float(step_raw.get("final_value_and_units", 0) or 0),
                    },
                    "step_by_step_audit": str(item.get("step_by_step_audit", "")).strip(),
                    "remediation_advice": str(item.get("remediation_advice", "")).strip(),
                }
            )

    if total_maximum <= 0 and normalized_breakdown:
        total_maximum = sum(float(item.get("max_marks", 0) or 0) for item in normalized_breakdown)
    if total_secured <= 0 and normalized_breakdown:
        total_secured = sum(float(item.get("allocated_marks", 0) or 0) for item in normalized_breakdown)

    percentage = (total_secured / total_maximum) * 100 if total_maximum > 0 else 0.0

    return {
        "test_id": test_id,
        "test_name": test_name or "",
        "test_number": test_number,
        "student_id": student_id,
        "student_name": student_name,
        "total_maximum_marks": round(total_maximum, 2),
        "total_secured_marks": round(total_secured, 2),
        "percentage_secured": f"{percentage:.2f}%",
        "concept_mastery_insights": {
            "strong_concepts": strong_concepts,
            "weak_concepts": weak_concepts,
        },
        "detailed_answer_breakdown": normalized_breakdown,
    }
