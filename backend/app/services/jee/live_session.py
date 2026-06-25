from google.cloud import firestore

db = firestore.Client()


class LiveSession:

    def __init__(self, question_id):

        self.question_id = question_id

        self.question = self._load_question()

    def _load_question(self):

        doc = db.collection(
            "student_questions"
        ).document(
            self.question_id
        ).get()

        if not doc.exists:
            return None

        return doc.to_dict()

    def build_context(self):

        if not self.question:
            return "Question not found"

        return f"""
Question:
{self.question['question_text']}

Answer:
{self.question['answer']}

Solution:
{self.question['solution']}
"""