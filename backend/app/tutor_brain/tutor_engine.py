from backend.app.tutor_brain.lesson_state import LessonState
from backend.app.services.ai_gateway import generate_response


class TutorEngine:
    def __init__(self):
        self.sessions = {}

    def process(self, session_id, message):
        
        print("TutorEngine called")

        # create state if new session
        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()

        state = self.sessions[session_id]
        print("STATE:", state.step)
        # STEP 1: INTRO
        if state.step == "INTRO":
            print("STEP: INTRO")
            state.step = "QUESTION"

            prompt = """
            You are a CBSE Class 10 math teacher.

            Teach Linear Equations in a simple step-by-step way.

            Rules:
            - Explain in very simple language
            - Use one example: 2x + 3 = 7
            - Solve step-by-step
            - Ask the student a question at the end

            Keep response short and interactive.
            """

            response = generate_response(prompt)

            print("Gemini response:", response)

            if not response or response == "None":
                return "Try again 😊"

            return str(response)

        # STEP 2: QUESTION
        elif state.step == "QUESTION":
            try:
                answer = int(message)

                if answer == 2:
                    state.step = "FEEDBACK"
                    return "Correct! x = 2 🎉"

                else:
                    prompt = f"""
                    You are a math teacher.

                    Student answered {answer} for equation 2x + 3 = 7.

                    Explain step-by-step:
                    1. What mistake student made
                    2. Correct solution
                    3. Ask student to try again

                    Keep it simple.
                    """

                    response = generate_response(prompt)

            except:
                return "No problem 😊 Let's solve it together.\n\nStep 1: Subtract 3 from both sides.\nWhat do you get?"

           
            
        # STEP 3: FEEDBACK
        elif state.step == "FEEDBACK":
            state.step = "QUESTION"
            return "Good! Now try again: What is x in 2x + 3 = 7?"