from google.cloud import firestore

from app.services.ai_gateway import (
    generate_response
)

from app.services.jee.chat_memory import (
    get_chat_history,
    save_message
)

db = firestore.Client()


def discuss_question(
    question_id,
    student_message
):

    doc = db.collection(
        "student_questions"
    ).document(
        question_id
    ).get()

    if not doc.exists:
        return {
            "error": "Question not found"
        }

    question = doc.to_dict()

    history = get_chat_history(
        question_id
    )

    conversation = ""

    for msg in history:
        conversation += (
            f"{msg['role']}: "
            f"{msg['content']}\n"
        )

    prompt = f"""
You are an expert JEE Mathematics teacher.

Current Question

{question}

Correct Answer

{answer}

Detailed Solution

{solution}

Student Doubt

{request.message}

Rules

1. Answer ONLY from the uploaded JEE Mathematics question.
2. Use the given solution as the primary source.
3. Explain step-by-step.
4. If student asks a follow-up doubt, answer only using the current question.
5. Never discuss politics.
6. Never discuss movies.
7. Never discuss cricket.
8. Never discuss religion.
9. Never discuss coding.
10. Never answer anything outside JEE Mathematics.

If the question is unrelated, reply exactly:

Let's stay focused on JEE Mathematics. Please ask a doubt related to the current problem.

Return plain text only.
Do not use markdown.
Do not use JSON.
"""

    response = generate_response(
        prompt
    )

    return {
        "response": response
    }