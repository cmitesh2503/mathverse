from backend.app.tutor_brain.lesson_state import LessonState
from backend.app.services.ai_gateway import generate_response
from backend.app.services.retrieval_service import retrieve_context
from backend.app.services.question_service import generate_question
from backend.app.services.evaluation_service import evaluate_answer
from backend.app.services.hint_service import get_hint

class TutorEngine:
    def __init__(self):
        self.sessions = {}

    def process(self, session_id, message):

        print("TutorEngine called")

        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()

        state = self.sessions[session_id]
        print("STATE:", state.step)

        # STEP 1: INTRO
        if state.step == "INTRO":

            context = retrieve_context("linear_equations")

            prompt = f"""
            You are a CBSE Class 10 math teacher.

            Use ONLY the below NCERT content to teach:

            {context}

            Explain simply and ask one question.
            """

            response = generate_response(prompt)

            state.step = "QUESTION"   # 🔥 IMPORTANT

            return response or "Let's start learning!"

        # STEP 2: QUESTION
        elif state.step == "QUESTION":

            # generate question if not exists
            if not hasattr(state, "current_question"):
                q = generate_question()
                state.current_question = q
                state.hint_level = 1

                return q["question"]

            # evaluate answer
            is_correct = evaluate_answer(message, state.current_question["answer"])

            if is_correct:
                state.step = "FEEDBACK"
                return "Correct! x = 2 🎉"

            else:
                hint = get_hint(state.hint_level)
                state.hint_level += 1

                return f"Not quite 😊\nHint: {hint}"

        # STEP 3: FEEDBACK
        elif state.step == "FEEDBACK":
            state.step = "QUESTION"
            del state.current_question   # reset

            return "Great! Next question coming..."