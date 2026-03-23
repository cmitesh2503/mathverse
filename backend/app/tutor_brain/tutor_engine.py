from backend.app.tutor_brain.lesson_state import LessonState
from backend.app.services.ai_gateway import generate_response
from backend.app.services.retrieval_service import retrieve_context

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
            
                answer = int(message)

                if answer == 2:
                    state.step = "FEEDBACK"
                    return "Correct! x = 2 🎉"

                else:
                    context = retrieve_context("linear_equations")

                    prompt = f"""
                    Use NCERT content below:

                    {context}

                    Student answered {answer}.

                    Explain step-by-step using NCERT method.
                    """

                    response = generate_response(prompt)

                    if not response:
                        return "No problem 😊 Let's solve it together.\n\nStep 1: Subtract 3 from both sides.\nWhat do you get?"
                    return response

        # STEP 3: FEEDBACK
        elif state.step == "FEEDBACK":
               state.step = "QUESTION"
        return "Good! Now try again: What is x in 2x + 3 = 7?"