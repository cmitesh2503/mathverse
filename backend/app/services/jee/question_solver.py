from google.genai import types

from app.services.ai_gateway import (
    _new_sdk_client
)


def solve_question_from_image(image_bytes):

    client = _new_sdk_client()

    prompt = """
You are an expert JEE Main Mathematics teacher.

Analyze the uploaded question image.

Return the response in EXACTLY the following format.

Do NOT add any extra headings.
Do NOT add markdown.
Do NOT add explanations.
Do NOT change the field order.

**Question:**
<Complete question>

**Chapter:**
<Only the chapter name>

**Answer:**
<Correct option only>

**Solution:**
<Complete step-by-step solution>

Rules:

1. Chapter must contain ONLY the chapter name.
2. Never include the solution inside the chapter.
3. Never include explanations before Answer.
4. Never omit any section.
5. Preserve the exact order above.
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