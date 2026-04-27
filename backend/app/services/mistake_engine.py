# This module defines the MistakeEngine class which is identifying common mistakes.
MISTAKE_TYPES = [
    "concept_error",
    "calculation_error",
    "careless_error"
]

# Define a function to check if the user's answer is correct
def is_correct(user_answer, correct_answer):
    return str(user_answer).strip() == str(correct_answer).strip()

# Define a function to classify the type of mistake based on the user's answer and the correct answer
def classify_mistake(user_answer, correct_answer):
    if is_correct(user_answer, correct_answer):
        return None

    try:
        ua = float(user_answer)
        ca = float(correct_answer)

        if abs(ua - ca) <= 2:
            return "calculation_error"
    except:
        pass

    return "concept_error"

# Define the MistakeEngine function which takes a question, the user's answer, and the correct answer, and returns the type of mistake
def extract_concept(question):
    # temporary placeholder
    if "quadratic" in question.lower():
        return "quadratics"
    return "general"

# Main function to analyze the user's attempt and return the mistake type and concept
def analyze_attempt(user_answer, correct_answer, question):
    correct = is_correct(user_answer, correct_answer)

    concept = extract_concept(question)

    if correct:
        return {
            "is_correct": True,
            "mistake_type": None,
            "concept": concept
        }

    mistake_type = classify_mistake(user_answer, correct_answer)

    return {
        "is_correct": False,
        "mistake_type": mistake_type,
        "concept": concept
    }