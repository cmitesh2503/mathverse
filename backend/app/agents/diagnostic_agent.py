from __future__ import annotations

try:
    from app.models.session import StudentSession
except ModuleNotFoundError:
    from ..models.session import StudentSession


class DiagnosticAgent:
    SYSTEM_PROMPT = """You are an expert mathematical diagnostic engine evaluating JEE-level math problems.
You NEVER speak directly to the user.
Your job is to compare the student's answer to the correct answer, identify the exact mathematical misstep, and write a strict, hidden directive for the live tutor.
Do not solve the problem. Categorize the error (e.g., 'sign_error', 'conceptual_gap', 'formula_error').
"""

    async def evaluate_answer(
        self,
        session: StudentSession,
        student_answer: str,
        correct_answer: str,
    ) -> dict:
        normalized_student_answer = student_answer.strip().lower()
        normalized_correct_answer = correct_answer.strip().lower()

        if normalized_student_answer == normalized_correct_answer:
            return {
                "is_correct": True,
                "error_category": "none",
                "hidden_nudge": None,
            }

        if "-" in normalized_student_answer and "-" not in normalized_correct_answer:
            return {
                "is_correct": False,
                "error_category": "sign_error",
                "hidden_nudge": "The student made a sign error. Ask them to double-check their positive and negative distributions.",
            }

        return {
            "is_correct": False,
            "error_category": "calculation_error",
            "hidden_nudge": "The student made a calculation error. Guide them to re-calculate the final step.",
        }
