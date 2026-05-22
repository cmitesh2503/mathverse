import os

from vertexai.generative_models import GenerativeModel
import vertexai

from dotenv import load_dotenv
import json
import re
import asyncio
import requests

vertexai.init(
    project="mathverse-live-ai",   # 👈 replace
    location="global"
)

model = GenerativeModel(os.getenv("GEMINI_PLANNER_MODEL", os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-pro-preview")))
#model = GenerativeModel("gemini-1.5-flash")

def call_gemini(prompt: str):
    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print("❌ VERTEX ERROR:", e)
        return None
    


async def call_gemini_async(prompt: str):
    loop = asyncio.get_running_loop()

    try:
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(prompt)
        )
        return response.text

    except Exception as e:
        print("❌ VERTEX ERROR:", e)
        return None




# ---------------------------
# 🔧 Clean RAG text
# ---------------------------
def clean_rag_text(text: str) -> str:
    text = text.replace("", "=")
    text = text.replace("\n", " ")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()


# ---------------------------
# 🧠 MAIN FUNCTION
# ---------------------------
async def build_lesson_plan(rag_text: str, mistake_type: str = None, exam: str = "cbse"):

    rag_text = clean_rag_text(rag_text)
    exam = (exam or "cbse").lower()

    # ---------------------------
    # 🔥 Mistake-aware instruction
    # ---------------------------
    mistake_instruction = ""

    if mistake_type == "sign_error":
        mistake_instruction = "Student made a sign mistake. Focus on + and - carefully."
    elif mistake_type == "missing_root":
        mistake_instruction = "Student missed one root. Emphasize that quadratic has two solutions."
    elif mistake_type == "calculation_error":
        mistake_instruction = "Student made a calculation mistake. Show correct steps clearly."
    elif mistake_type == "format_error":
        mistake_instruction = "Student input format is wrong. Explain proper format."
    else:
        mistake_instruction = "Explain clearly step-by-step."

    # ---------------------------
    # 🔥 GEMINI PROMPT
    # ---------------------------
    tutor_style = (
        "You are an expert JEE math tutor. Keep it short, fast, and exam-oriented. "
        "Use direct solving steps, one shortcut trick, and one quick mental check. "
        "Do not refer to NCERT, textbook context, or RAG sources."
        if exam == "jee"
        else
        f"Explain like a school teacher to a Class {{grade}} student.\n"
        "- Use very simple words\n"
        "- Use short sentences\n"
        "- Use one real-life analogy\n"
        "- Avoid jargon\n"
        "- Max 3-4 steps per example\n"
        "- Do not rush to solution\n"
        "Use the provided NCERT/CBSE context and follow the chapter order."
    )
    max_steps = 3 if exam == "jee" else 5

    prompt = f"""
    {tutor_style}

    Question context:
    {rag_text}

    Student mistake:
    {mistake_instruction}

    Your job:
    1. Explain ONLY based on the mistake
    2. Keep explanation within max {max_steps} steps
    3. Match the requested exam style

    Special rules:
    - If missing_root → emphasize there are TWO roots
    - If sign_error → highlight sign handling clearly
    - If calculation_error → show exact correction
    - Avoid generic explanation
    - Use actual mathematical signs and symbols (e.g. √, π, ×, ÷, ^) in concept_steps instead of words like "sqrt".
    - In mistake_explanation, spell out the symbols (e.g., "square root", "times") so they are pronounced correctly.

    Also include:
    - 1 shortcut trick
    - 1 quick mental check

    Return ONLY JSON:

    {{
    "concept_steps": ["Step 1...", "Step 2...", "Step 3..."],
    "mistake_explanation": "Explain what student did wrong",
    "shortcut": "Quick trick",
    "mental_check": "Quick way to verify answer",
    "speed_hint": "Fast exam-solving hint"
    }}
    """

    try:
        text = await call_gemini_async(prompt)

        if not text:
            raise ValueError("No response from Gemini")

        text = text.strip()

        # ---------------------------
        # 🔥 Extract JSON safely
        # ---------------------------
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            data = json.loads(match.group())

            return {
                "concept_steps": data.get("concept_steps", []),
                "mistake_explanation": data.get("mistake_explanation", ""),
                "shortcut": data.get("shortcut", ""),
                "mental_check": data.get("mental_check", ""),
                "speed_hint": data.get("speed_hint", "")
            }

        raise ValueError("Invalid JSON")

    except Exception as e:
        print("❌ GEMINI ERROR:", e)

        # ---------------------------
        # 🔁 FALLBACK (IMPORTANT)
        # ---------------------------
        return {
            "concept_steps": [
                "Step 1: Rewrite equation",
                "Step 2: Solve carefully",
                "Step 3: Verify both roots"
            ],
            "mistake_explanation": "Check your steps carefully",
            "shortcut": "Use factorization when possible",
            "mental_check": "Multiply roots to verify",
            "speed_hint": "Use the fastest valid method, then verify by substitution."
        }
