from datetime import datetime
from google.cloud import firestore

db = firestore.Client()


def save_question(
    question_text,
    chapter,
    answer,
    solution
):

    doc_ref = (
        db.collection(
            "student_questions"
        )
        .document()
    )

    doc_ref.set({

        "question_id": doc_ref.id,

        "question_text": question_text,

        "chapter": chapter,

        "answer": answer,

        "solution": solution,

        "created_at": datetime.utcnow()

    })

    return doc_ref.id


def get_question(question_id):

    doc = (
        db.collection(
            "student_questions"
        )
        .document(question_id)
        .get()
    )

    if not doc.exists:
        return None

    return doc.to_dict()


def update_question(
    question_id,
    data
):

    db.collection(
        "student_questions"
    ).document(
        question_id
    ).update(
        data
    )


def delete_question(
    question_id
):

    db.collection(
        "student_questions"
    ).document(
        question_id
    ).delete()