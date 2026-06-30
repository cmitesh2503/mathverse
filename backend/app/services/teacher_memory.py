from dataclasses import dataclass, field


@dataclass
class TeacherMemory:

    explained_topics: list = field(
        default_factory=list
    )

    misconceptions: list = field(
        default_factory=list
    )
    teaching_methods_used: list = field(
        default_factory=list
    )
    learning_status: str = ""

    student_questions: list = field(
        default_factory=list
    )

    teacher_answers: list = field(
        default_factory=list
    )

    last_student_question: str = ""

    last_teacher_response: str = ""

    current_topic: str = ""

    def remember_question(
        self,
        question: str
    ):

        self.last_student_question = question

        self.student_questions.append(
            question
        )

    def remember_answer(
        self,
        answer: str
    ):

        self.last_teacher_response = answer

        self.teacher_answers.append(
            answer
        )

    def add_topic(
        self,
        topic: str
    ):

        if topic not in self.explained_topics:

            self.explained_topics.append(
                topic
            )

    def add_misconception(
        self,
        misconception: str
    ):

        if misconception not in self.misconceptions:

            self.misconceptions.append(
                misconception
            )
    def add_teaching_method(
            self,
            method: str
        ):

            if method not in self.teaching_methods_used:

                self.teaching_methods_used.append(
                    method
                )
                
    def set_learning_status(
        self,
        status: str
    ):

        self.learning_status = status