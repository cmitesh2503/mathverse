from app.services.jee.tutor_context import TutorContext
from app.services.jee.chat_memory import (
    save_message,
    get_chat_history
)

from app.services.teacher_brain import (
    TeacherBrain
)


brain = TeacherBrain()


def discuss_question(
    question_id: str,
    student_message: str
):

    context = TutorContext.load(
        question_id
    )

    save_message(
        question_id,
        "student",
        student_message
    )

    history = get_chat_history(
        question_id
    )

    context["history"] = history

    response = brain.chat(
        context,
        student_message
    )
    
    

    save_message(
        question_id,
        "tutor",
        response
    )

    return {

        "response": response

    }