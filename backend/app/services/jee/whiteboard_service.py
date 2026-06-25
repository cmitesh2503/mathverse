import json

from app.services.ai_gateway import (
    generate_response
)


def generate_whiteboard(
    question,
    solution,
    doubt
):

    prompt = f"""
Question:
{question}

Solution:
{solution}

Student Doubt:
{doubt}

Return ONLY valid JSON.

Example:

{{
  "exercise_no":"Q1",
  "problem":"Why median is 18?",
  "steps":[
    "Total students N=40",
    "Need 20th and 21st observations",
    "CF upto 17 = 18",
    "CF upto 18 = 30",
    "20th and 21st lie in age 18",
    "Median = 18"
  ]
}}

Do not return explanation.
Do not return markdown.
Do not return text outside JSON.
"""

    try:

        response = generate_response(
            prompt,
            response_schema=None
        )

        print("=" * 50)
        print("WHITEBOARD RESPONSE")
        print(response)
        print("=" * 50)

        response = response.strip()

        if response.startswith("```json"):
            response = response.replace("```json", "", 1)

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        return json.loads(response)

    except Exception as e:

        print("WHITEBOARD ERROR")
        print(e)

        return {
            "exercise_no": "Q1",
            "problem": doubt,
            "steps": [
                "Whiteboard generation failed"
            ]
        }