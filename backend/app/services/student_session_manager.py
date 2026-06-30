from app.services.student_session_model import (
    StudentSessionModel
)


class StudentSessionManager:

    def __init__(self):

        self.sessions = {}

    def get_session(
        self,
        question_id: str,
        chapter: str = ""
    ) -> StudentSessionModel:

        if question_id not in self.sessions:

            self.sessions[
                question_id
            ] = StudentSessionModel(

                question_id=question_id,

                chapter=chapter
            )

        return self.sessions[
            question_id
        ]

    def remove_session(
        self,
        question_id: str
    ):

        self.sessions.pop(
            question_id,
            None
        )

    def clear(self):

        self.sessions.clear()