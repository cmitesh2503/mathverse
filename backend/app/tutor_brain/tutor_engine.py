from backend.app.tutor_brain.lesson_state import LessonState
from backend.app.services.ai_gateway import generate_response
from backend.app.services.retrieval_service import retrieve_context
from backend.app.services.question_service import generate_question
from backend.app.services.evaluation_service import evaluate_answer
from backend.app.services.hint_service import get_hint
from backend.app.services.progress_service import save_progress

class TutorEngine:
    def __init__(self):
        self.sessions = {}

    def process(self, session_id, message):

        print("TutorEngine called")

        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()

        state = self.sessions[session_id]
        print("STATE:", state.step)
        print("SESSION:", session_id)
        print("MESSAGE:", message)

        # STEP 1: INTRO
        if state.step == "INTRO":

            context = retrieve_context("linear_equations")
            
            
            
            prompt = f"""
            You are a CBSE Class 10 math teacher.

            Use ONLY the below NCERT content to teach:

            {context}

            Explain simply and ask one question.
            """
            print("PROMPT:", prompt)
            response = generate_response(prompt)

            state.step = "QUESTION"   # 🔥 IMPORTANT
            
            print("AI RESPONSE:", response)
            return response or "Let's start learning!"

        # STEP 2: QUESTION
        elif state.step == "QUESTION":

            print("QUESTION STEP")
            print("USER ANSWER:", message)

            if message.lower() in ["hi", "hello", "hey"]:
                return "We are solving: 2x + 3 = 7 😊\nWhat is x?"

            try:
                answer = int(message)

                if answer == 2:
                    state.step = "FEEDBACK"
                    return "Correct! x = 2 🎉"

                else:
                    context = retrieve_context("linear_equations")

                    prompt = f"""
                    Use NCERT content:

                    {context}

                    Student answered {answer}.
                    Explain step-by-step.
                    """

                    print("PROMPT:", prompt)

                    response = generate_response(prompt)

                    print("AI RESPONSE:", response)

                    if not response:
                        return "Let's solve this step by step 😊"

                    return response

            except:
                return "No problem 😊\n\nStep 1: Subtract 3 from both sides.\n2x = 4\nNow what is x?"
   
            

            # 🔥 SAVE PROGRESS
            save_progress(
                student_id=session_id,
                question=state.current_question["question"],
                correct=is_correct,
                hints_used=state.hint_level - 1
            )

            if is_correct:
                state.step = "FEEDBACK"
                return "Correct! x = 2 🎉"
        # STEP 3: FEEDBACK
        elif state.step == "FEEDBACK":
            state.step = "QUESTION"
            if hasattr(state, "current_question"):
                del state.current_question

            state.hint_level = 1
            return "Great! Next question coming..."