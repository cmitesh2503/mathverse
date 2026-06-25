from google.cloud import firestore

db = firestore.Client()


def save_message(
    question_id,
    role,
    content
):
    db.collection(
        "question_chats"
    ).document(
        question_id
    ).collection(
        "messages"
    ).add(
        {
            "role": role,
            "content": content
        }
    )


def get_chat_history(
    question_id
):
    docs = db.collection(
        "question_chats"
    ).document(
        question_id
    ).collection(
        "messages"
    ).stream()

    history = []

    for doc in docs:
        history.append(
            doc.to_dict()
        )

    return history