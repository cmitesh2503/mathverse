class LessonState:
    def __init__(self):
        self.step = "INTRO" # Intro -> TEACHING -> AWAITING_ANSWER -> CONCEPT_MASTERED -> NEXT_CONCEPT
        self.expected_answer: str = None
        self.grade: int = 10
        
        # Curriculum tracking
        self.topic: str = "linear_equations"
        self.current_concept_id: str = "simple_equations"
        self.current_concept = None
        
        # Progress tracking
        self.correct_answers_in_concept: int = 0
        self.total_attempts: int = 0
        self.mastery_threshold: int = 3  # Need 3 correct to move to next concept
        self.current_question_index: int = 0
        self.current_question = None
        self.current_answer = None