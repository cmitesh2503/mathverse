from .lesson_state import LessonState
from .curriculum import get_topic, get_concept, get_next_concept
import re

class TutorEngine:
    def __init__(self):
        self.sessions = {}
        self.doubt_keywords = ["don't understand", "dont understand", "confused", "doubt", "why", "how"]
        self.break_keywords = ["pause", "stop", "break", "rest"]
        self.ready_keywords = ["ready", "yes", "start", "begin", "ok", "okay"]
        self.greeting_keywords = ["hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"]

    def is_doubt(self, message: str) -> bool:
        lower = message.lower()
        return any(k in lower for k in self.doubt_keywords)

    def is_break(self, message: str) -> bool:
        lower = message.lower()
        return any(k in lower for k in self.break_keywords)

    def is_ready(self, message: str) -> bool:
        lower = message.lower().strip()
        return any(k in lower for k in self.ready_keywords)

    def is_greeting(self, message: str) -> bool:
        lower = message.lower().strip()
        return lower in self.greeting_keywords

    def extract_number(self, message: str):
        """Extract number from user message"""
        numbers = re.findall(r'-?\d+\.?\d*', message)
        if numbers:
            return float(numbers[0])
        return None

    def process(self, session_id, message):
        print("TutorEngine called")

        if session_id not in self.sessions:
            self.sessions[session_id] = LessonState()

        state = self.sessions[session_id]
        print(f"STATE: {state.step}, CONCEPT: {state.current_concept_id}")

        # Auto-start lesson when connection opens (empty message)
        if not message.strip()
            if state.step  ""
                state.step  "_"
                response  """ello everyone! elcome to today's ath class!

'm **va**, your ath eacher. oday we're going to learn about **inear quations** - one of the most important topics in mathematics.

inear equations help us solve real-world problems like
- ow much money will you have after saving $ each week
- f a train travels at  km/h, how long will it take to go  km
- hat temperature is  degrees  in elsius

hese equations have the form **ax + b  c**

here
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

et me explain this step by step, just like in a real classroom! 📚"""
                return response

inear equations help us solve real-world problems like
- ow much money will you have after saving $ each week
- f a train travels at  km/h, how long will it take to go  km
- hat temperature is  degrees  in elsius

hese equations have the form **ax + b  c**

here
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

et me explain this step by step, just like in a real classroom!"""
                return response
            else
                # uring lesson - acknowledge and continue
                return "ello! 'm here to help you learn. hat would you like to know about linear equations"

        # andle questions and doubts at any time during the lesson
        if self.is_doubt(message) or "" in message or message.lower().startswith(("what", "how", "why", "explain", "tell me"))
            if state.current_concept
                return f""" understand your question! et me explain **{state.current_concept'name']}** again.

**{state.current_concept'name']}**
{state.current_concept'description']}

**xample**
{state.current_concept'example_problem']}

**olution teps**
{chr().join(f"{i+}. {step}" for i, step in enumerate(state.current_concept'steps']))}

oes this help ou can ask me anything about linear equations! 🤔"""
            else
                return """🤔 reat question! 'm here to help you understand linear equations.

 **linear equation** is an equation that makes a straight line when graphed. he general form is **ax + b  c**, where
- **a** is the coefficient of x
- **x** is the variable we're solving for  
- **b** and **c** are constants

sk me anything specific about linear equations and 'll explain it! 📝"""

        # andle interruptions and clarifications
        if self.is_break(message)
            return "ure, let's take a short break. ype 'ready' or 'continue' when you're prepared to learn again. ⏸️"

        #    - reet and introduce the topic
        if state.step  ""
            state.step  "_"
            response  """ello everyone! elcome to today's ath class!

'm **va**, your ath eacher. oday we're going to learn about **inear quations** - one of the most important topics in mathematics.

inear equations help us solve real-world problems like
- ow much money will you have after saving $ each week
- f a train travels at  km/h, how long will it take to go  km
- hat temperature is  degrees  in elsius

hese equations have the form **ax + b  c**

here
- **a** is the coefficient of x
- **x** is the variable we want to find
- **b** and **c** are constants

et me explain this step by step, just like in a real classroom! 📚"""
            return response

        #     - xplain the concept
        elif state.step  "_"
            if self.is_ready(message)
                state.step  "_"
                response  """erfect! et's dive into **inear quations**.

**hat is a inear quation**

 linear equation is an equation that makes a straight line when graphed. he standard form is

**ax + b  c**

here
- **a**  coefficient (number multiplying x)
- **x**  variable (what we're solving for)
- **b**  constant term
- **c**  another constant

**xample  imple quation**
**x +   **

o solve
. ubtract  from both sides x +  -    - 
. **x  **

**xample  ith multiplication**
**x +   **

o solve
. ubtract  from both sides x +  -    - 
. x  
. ivide by  **x  **

**xample  ore complex**
**x -   **

o solve
. dd  to both sides x -  +    + 
. x  
. ivide by  **x  **

ow that you understand the basics, let's practice some problems together! ype "practice" to start solving equations. 🎯"""
                return response
            else
                return "ake your time to read the introduction. ype 'ready' when you're prepared to learn about linear equations!"

        #     - ait for practice request
        elif state.step  "_"
            if message.lower() in "practice", "start", "begin", "let's practice"]
                # nitialize first concept
                topic  get_topic("linear_equations")
                state.current_concept  get_concept("linear_equations", "simple_equations")
                state.current_concept_id  "simple_equations"
                
                response  f"""xcellent! et's start with **{state.current_concept'name']}**.

{state.current_concept'description']}

**xample roblem**
{state.current_concept'example_problem']}

**olution teps**
{chr().join(f"{i+}. {step}" for i, step in enumerate(state.current_concept'steps']))}

ow it's your turn! olve this practice problem
**{state.current_concept'practice_problems']]'equation']}**

hat is x (ust type the number)"""
                state.current_question  state.current_concept'practice_problems']]'equation']
                state.current_answer  state.current_concept'practice_problems']]'answer']
                state.current_question_index  
                state.step  "_"
                return response
            else
                return "reat! ow that you understand linear equations, type 'practice' to start solving problems together!"

        #     - heck student solution
        elif state.step  "_"
            user_answer  self.extract_number(message)
            
            if user_answer is one
                return f" need a number answer. olve **{state.current_question}**nnhat is x"
            
            state.total_attempts + 
            
            # heck if answer is correct
            if abs(user_answer - state.current_answer)  .
                state.correct_answers_in_concept + 
                
                if state.correct_answers_in_concept  state.mastery_threshold
                    state.step  "_"
                    response  f"""🎉 xcellent! ou got it right! x  {int(user_answer)} ✓

ou've now answered **{state.correct_answers_in_concept}** questions correctly in this concept!

🏆 ou've mastered **{state.current_concept'name']}**!

eady to move to the next concept ype "next" to continue! 📚"""
                    return response
                else
                    # sk next practice problem
                    state.current_question_index + 
                    if state.current_question_index  len(state.current_concept'practice_problems'])
                        next_prob  state.current_concept'practice_problems']state.current_question_index]
                        state.current_question  next_prob'equation']
                        state.current_answer  next_prob'answer']
                        
                        response  f"""✅ orrect! x  {int(user_answer)}nnreat work! {state.mastery_threshold - state.correct_answers_in_concept} more to master this concept.nnext problem
**{next_prob'equation']}**

hat is x"""
                        return response
                    else
                        # un out of problems, mark as mastered
                        state.step  "_"
                        response  f"""✅ orrect! x  {int(user_answer)}

🏆 ou've mastered **{state.current_concept'name']}**!

eady for the next challenge ype "next"! 📚"""
                        return response
            else
                # rong answer - show solution
                response  f"""ot quite. ou got x  {int(user_answer)}, but the correct answer is x  {int(state.current_answer)}.

olution steps
{chr().join(f"{i+}. {step}" for i, step in enumerate(state.current_concept'steps']))}

et's try another problem from this concept
**{state.current_concept'practice_problems']state.current_question_index]'equation']}**

hat is x"""
                return response

        #     - ffer next concept
        elif state.step  "_"
            if self.is_ready(message) or message.lower() in "next", "continue"]
                next_concept  get_next_concept("linear_equations", state.current_concept_id)
                
                if next_concept
                    # ove to next concept
                    state.current_concept_id  next_concept'id']
                    state.current_concept  next_concept
                    state.correct_answers_in_concept  
                    state.current_question_index  
                    state.step  "_"
                    
                    first_prob  next_concept'practice_problems']]
                    state.current_question  first_prob'equation']
                    state.current_answer  first_prob'answer']
                    
                    response  f"""xcellent! oving to the next concept! 🚀

**oncept {next_concept'name']}**

{next_concept'description']}

**xample**
{next_concept'example_problem']}

olution steps
{chr().join(f"{i+}. {step}" for i, step in enumerate(next_concept'steps']))}

ow your turn! olve
**{first_prob'equation']}**

hat is x"""
                    state.step  "_"
                    return response
                else
                    response  """🎓 ongratulations! ou've completed all concepts in **inear quations**!

ou're now a master of linear equations! ell done! 🏆

ould you like to review any concept or move to a new topic"""
                    state.step  "_"
                    return response
            else
                return "ype 'next' when ready for the next concept! 📚"

        elif state.step  "_"
            return "reat job! ou've completed this topic. tart a new lesson to continue learning!"

        return "et's continue learning! end me a message. 😊"

    def build_prompt(self, session_id str, message str) - str
        return f"xplain simply {message}"
