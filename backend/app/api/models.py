from pydantic import BaseModel
from typing import Optional, Dict, Any

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