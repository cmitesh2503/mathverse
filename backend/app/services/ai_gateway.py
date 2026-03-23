import google.generativeai as genai
from backend.app.core.config import GEMINI_API_KEY

print("API KEY:", GEMINI_API_KEY)  # Debug print to verify API key is loaded
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-pro")  # safer model


def generate_response(prompt: str) -> str:
    try:
        #print("Calling Gemini...")

        response = model.generate_content(prompt)
        #return str(response)

        print("RAW RESPONSE:", response)
        
    except Exception as e:
        print("Gemini API Error:", e)
        return "Something went wrong. Please try again."

        # SAFEST extraction
        if response.candidates:
            parts = response.candidates[0].content.parts
            if parts and hasattr(parts[0], "text"):
                return parts[0].text

        return "Let me explain step by step."

    except Exception as e:
        print("Gemini Error:", e)
        return "Something went wrong. Please try again."