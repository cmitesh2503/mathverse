import google.generativeai as genai
import os

# Do not auto-load .env in production; allow explicit env setup for local dev.
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-pro")

response = model.generate_content("Solve x^2 - 4 = 0")

print(response.text)