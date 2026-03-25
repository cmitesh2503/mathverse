import google.generativeai as genai
from backend.app.core.config import GEMINI_API_KEY
from backend.app.cache.cache_manager import get_cache, set_cache
from backend.app.guardrails.ai_guardrail import validate_response

print("API KEY:", GEMINI_API_KEY)  # Debug print to verify API key is loaded
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("models/gemini-1.5-flash")  # safer model


def generate_response(prompt: str) -> str:
    
    def generate_response(prompt: str) -> str:

        print("AI CALL START")
        print("PROMPT:", prompt)

        cached = get_cache(prompt)
        if cached:
            print("CACHE HIT")
            return cached

        try:
            response = model.generate_content(prompt)

            if response and hasattr(response, "text") and response.text:
                text = response.text.strip()

                text = validate_response(text)

                set_cache(prompt, text)

                print("RAW RESPONSE:", response)

                return text

            return None

        except Exception as e:
            print("Gemini API Error:", e)
            return None