from backend.app.tutor_brain.lesson_state import LessonState

class TutorEngine:
    def __init__(self):
        self.sessions = {}
        
    def process(self, session_id, message):
        
        # create state if new session
        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()
        
        state = self.sessions[session_id]
        
         # STEP 1: INTRO
        if state.step == "Intro":
            state.step = "Question"
            return "Let's learn Linear Equations. What is x in 2x + 3 = 7?"
        
        # STEP 2: QUESTION → check answer
        elif state.step == "Question":
            try:
                answer = int(message)
                if answer == 2:
                    state.step = "Feedback"
                    return "Correct! x = 2. Great job 🎉"
                else:
                    return "Correct! x = 2. Great job 🎉"
            except:
                return "Please enter a number."
            
        # STEP 3: FEEDBACK
        elif state.step == "FEEDBACK":
            return "Let's try another question soon!"
        