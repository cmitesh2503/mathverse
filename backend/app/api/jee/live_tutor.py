from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.services.jee.live_session import LiveSession
from app.services.ai_gateway import generate_response
from app.services.jee.chat_memory import (
    save_message,
    get_chat_history
)
from app.services.jee.whiteboard_service import (
    generate_whiteboard
)

import json

router = APIRouter()


@router.websocket("/live-tutor")
async def live_tutor(
    websocket: WebSocket
):

    await websocket.accept()

    try:

        question_id = await websocket.receive_text()

        session = LiveSession(
            question_id
        )

        while True:

            student_message = (
                await websocket.receive_text()
            )

            save_message(
                question_id,
                "student",
                student_message
            )

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
You are discussing an already solved JEE Main question.

Question:
{session.question['question_text']}

Answer:
{session.question['answer']}

Solution:
{session.question['solution']}

Conversation History:
{conversation}

Student Doubt:
{student_message}

Important Rules:

1. Use ONLY the question above.
2. Use ONLY the solution above.
3. Never say "question is missing".
4. Never say "data is not provided".
5. Student is asking about THIS exact question.

Answer as an Indian JEE Mathematics teacher.

Rules:
1. Speak conversationally.
2. Explain step-by-step.
3. Address student as "beta" occasionally.
4. Never read formulas mechanically.
5. Never return JSON.
6. Never return markdown.
7. Keep response under 120 words.
8. Explain like you are standing in front of a classroom.
9. Focus only on the student's doubt.
10. Use simple spoken English.
11. You are ONLY a JEE Mathematics Tutor.
12. Only answer questions related to the uploaded JEE Mathematics problem.
13. If student asks anything unrelated to mathematics:
   reply:

   "Let's stay focused on JEE Mathematics. Please ask a doubt related to the current problem."

14. Never discuss politics.
15. Never discuss movies.
16. Never discuss cricket.
17. Never discuss religion.
18. Never discuss general knowledge.
19. Never answer coding questions.
20. Never answer personal advice questions.

Return plain text only.
Do not return JSON.
"""

            response = generate_response(
                prompt,
                response_schema=None
            )

            whiteboard = generate_whiteboard(
                session.question["question_text"],
                session.question["solution"],
                student_message
            )

            save_message(
                question_id,
                "tutor",
                response
            )

            await websocket.send_text(
                json.dumps(
                    {
                        "explanation": response,
                        "whiteboard": whiteboard
                    }
                )
            )

    except WebSocketDisconnect:

        print(
            f"Student disconnected: {question_id}"
        )

    except Exception as e:

        print(
            f"Live Tutor Error: {e}"
        )