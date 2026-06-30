import json

from app.services.ai_gateway import generate_structured_response
from app.models.memory_schema import MemorySchema


class MemoryExtractor:

    def extract(
        self,
        student_message: str,
        teacher_response: str
    ) -> dict:

        prompt = f"""
You are updating an AI teacher's long-term teaching memory.

Student Question
----------------
{student_message}

Teacher Response
----------------
{teacher_response}

Extract ONLY the educational memory that a human teacher would remember for the next interaction.

Focus on:

• mathematical topic

• concepts already explained

• student misconceptions

• what the student is struggling with

Do NOT summarize the teacher response.

Extract only reusable teaching memory.

Return ONLY valid JSON.

Required format:

{{
    "current_topic": "",

    "explained_topics": [],

    "misconceptions": [],

    "teaching_methods_used": [],

    "learning_status": ""
}}

Rules

1. current_topic must contain ONLY the main mathematical concept.

2. explained_topics must contain ONLY concept names.

Example:
Good concepts

Median
Mean Deviation
Frequency Distribution
Cumulative Frequency
Variance
Probability

Do NOT store

Variables

x
y
Age (x_i)
Table
Option A
Student
Numbers

Never explanation sentences.

3. misconceptions must contain ONLY misconceptions.

4. teaching_methods_used must contain only values from:

    Explanation
    Example
    Analogy
    Hint
    Whiteboard
    Check Understanding

5. learning_status must be exactly one of:

Confused
Learning
Understood
Mastered

6. Never invent information.

7. Return JSON only.

8. Never infer a chapter different from the supplied chapter.

9. Never create topics unrelated to the supplied question.

10.If uncertain, use the supplied chapter instead of guessing.

11.Maximum explained_topics = 2.

12.Choose the two most important mathematical concepts only.

13.Never store notation.

14.Never store variable names.

15.Never store table headings.
"""

        response = generate_structured_response(
            prompt,
            response_schema=MemorySchema
        )

        print("=" * 60)
        print("MEMORY RESPONSE TYPE")
        print(type(response))
        print("=" * 60)

        print("=" * 60)
        print("MEMORY RAW RESPONSE")
        print(response)
        print("=" * 60)
        
        if isinstance(response, MemorySchema):

            return response.model_dump()

        if isinstance(response, dict):

            return response

        return {
            "current_topic": "",
            "explained_topics": [],
            "misconceptions": []
        }
        
        