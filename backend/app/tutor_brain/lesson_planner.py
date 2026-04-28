import os

from vertexai.generative_models import GenerativeModel
import vertexai

from dotenv import load_dotenv
import json
import re

import requests

vertexai.init(
    project="mathverse-live-ai",   # 👈 replace
    location="global"
)

model = GenerativeModel("gemini-2.5-pro")


def call_gemini(prompt: str):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("❌ VERTEX ERROR:", e)
        return None

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("❌ REQUEST ERROR:", e)
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
def build_lesson_plan(rag_text: str, mistake_type: str = None):

    rag_text = clean_rag_text(rag_text)

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
    prompt = f"""
You are a CBSE + JEE math tutor.

Content:
{rag_text}

Student mistake:
{mistake_instruction}

Task:
1. Explain solution step-by-step (max 3 steps)
2. Keep it simple and clean
3. Give 1 short example
4. Explain mistake clearly

Return ONLY JSON:

{{
  "concept_steps": ["Step 1...", "Step 2...", "Step 3..."],
  "examples": ["Example..."],
  "mistake_explanation": "Explain what student did wrong"
}}
"""

    try:
        text = call_gemini(prompt)

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
                "examples": data.get("examples", []),
                "mistake_explanation": data.get("mistake_explanation", "")
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
                "Step 2: Solve step-by-step",
                "Step 3: Verify answer"
            ],
            "examples": ["Try solving a similar equation"],
            "mistake_explanation": "Review your steps carefully"
        }