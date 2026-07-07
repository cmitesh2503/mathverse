import google.generativeai as genai
import os
from app.core import config

# Do not auto-load .env in production; allow explicit env setup for local dev.
genai.configure(
    api_key=config.GEMINI_API_KEY
)

model = genai.GenerativeModel("gemini-pro")

response = model.generate_content("Solve x^2 - 4 = 0")

print(response.text)