import os
import google.generativeai as genai

# Make sure your GEMINI_API_KEY environment variable is set
api_key = os.getenv("GEMINI_API_KEY") 
genai.configure(api_key=api_key)

print("Models available on your account:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        if 'gemini-3' in m.name or 'gemini-1.5' in m.name:
            print(m.name)