from google.genai import types

from app.services.ai_gateway import (
    _new_sdk_client
)


def solve_question_from_image(image_bytes):

    client = _new_sdk_client()

    prompt = """
    You are an expert JEE Main Mathematics teacher.

    Analyze the uploaded question image.

    Return:

    Question:
    Chapter:
    Answer:
    Solution:
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ]
    )

    return response.text