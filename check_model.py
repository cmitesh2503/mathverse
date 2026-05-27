import os
from pathlib import Path

import google.generativeai as genai

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")
except ImportError:
    pass

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env before listing models.")

genai.configure(api_key=api_key)

print("Models available on your account:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
