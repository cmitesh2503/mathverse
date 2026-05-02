from pydantic import BaseModel
from typing import Dict, Any, Optional


class TutorRequest(BaseModel):
    session_id: str
    mode: str   # "practice" | "learn" | "doubt" | "ocr" | "homework"

    input: Dict[str, Any]
    # example:
    # {
    #   "question": "x^2 - 5x + 6 = 0",
    #   "answer": "2,3"
    # }

    context: Optional[Dict[str, Any]] = None
    # example:
    # {
    #   "exam": "jee",        # "cbse" | "jee"
    #   "level": "advanced",  # future use
    #   "goal": "speed"       # future use
    # }

    def get_exam(self) -> str:
        """
        Safe helper:
        - defaults to CBSE
        - prevents crashes if context is None
        """
        if self.context and "exam" in self.context:
            return self.context["exam"]
        return "cbse"

    def get_student_id(self) -> str:
        if self.context and self.context.get("student_id"):
            return str(self.context["student_id"])
        return self.session_id
