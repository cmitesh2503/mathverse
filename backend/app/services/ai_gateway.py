import google.generativeai as genai
from ..core.config import GEMINI_API_KEY
from ..cache.cache_manager import get_cache, set_cache
from ..guardrails.ai_guardrail import validate_response
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

genai.configure(api_key=GEMINI_API_KEY)

def list_available_models():
    """List all available models from Gemini API"""
    try:
        for model in genai.list_models():
            print(f"Model: {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

def generate_response(prompt: str) -> str:

    print("AI CALL START")
    print("PROMPT:", prompt)
    
    #print("AVAILABLE MODELS:")
    #for m in client.models.list():
    #    print(m.name)

    cached = get_cache(prompt)
    if cached:
        print("CACHE HIT")
        return cached

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        text = response.text if response.text else "Let’s solve step by step 😊"

        text = validate_response(text)
        set_cache(prompt, text)

        return text

    except Exception as e:
        print("Gemini API Error:", e)
        return "Let’s solve step by step 😊"
    
async def stream_response(prompt: str):
    print("AI STREAM START")
    print("PROMPT:", prompt)

    # ✅ 1. Cache check (important)
    cached = get_cache(prompt)
    if cached:
        print("CACHE HIT (STREAM)")
        for word in cached.split():
            yield word + " "
            await asyncio.sleep(0.01)
        return

    try:
        # ✅ 2. Gemini streaming call
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt, stream=True)

        full_text = ""

        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield chunk.text  # 🔥 real streaming

        # ✅ 3. Guardrail AFTER full response
        full_text = validate_response(full_text)

        # ✅ 4. Cache final validated response
        set_cache(prompt, full_text)

    except Exception as e:
        print("Gemini STREAM Error:", e)

        # ✅ 5. Fallback to non-stream
        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
            )

            text = response.text if response.text else "Let’s solve step by step 😊"
            text = validate_response(text)
            set_cache(prompt, text)

            for word in text.split():
                yield word + " "
                await asyncio.sleep(0.02)

        except Exception as e:
            print("Fallback Error:", e)
            yield "Let’s solve step by step 😊"