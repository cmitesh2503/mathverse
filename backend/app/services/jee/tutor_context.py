from app.services.jee.question_repository import get_question

from app.services.jee.chat_memory import (
    get_chat_history
)


class TutorContext:

    @staticmethod
    def load(question_id: str):

        question = get_question(question_id)

        if not question:

            raise Exception(
                f"Question not found: {question_id}"
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

        return {

            "question_id": question_id,

            "question":
                question["question_text"],

            "answer":
                question["answer"],

            "solution":
                question["solution"],

            "chapter":
                question.get(
                    "chapter",
                    ""
                ),

            "difficulty":
                question.get(
                    "difficulty",
                    "JEE Main"
                ),

            "image":
                question.get(
                    "image",
                    ""
                ),

            "history":
                history,

            "conversation":
                conversation
        }