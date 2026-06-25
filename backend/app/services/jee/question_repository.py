from datetime import datetime
from google.cloud import firestore

db = firestore.Client()


def save_question(
    question_text,
    chapter,
    answer,
    solution
):
    doc_ref = db.collection(
        "student_questions"
    ).document()

    doc_ref.set({
        "question_id": doc_ref.id,
        "question_text": question_text,
        "chapter": chapter,
        "answer": answer,
        "solution": solution,
        "created_at": datetime.utcnow()
    })

    return doc_ref.id