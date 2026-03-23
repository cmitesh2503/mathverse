def evaluate_answer(student_answer, correct_answer):
    try:
        return int(student_answer) == correct_answer
    except:
        return False