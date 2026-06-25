from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project="matverse",
    location="us-central1"
)

def transcribe_audio(audio_bytes):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Transcribe this audio exactly.",
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/webm"
            )
        ]
    )

    return response.text