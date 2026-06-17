import json
import re
from datetime import datetime

from google.cloud import storage
from google.cloud import firestore

storage_client = storage.Client()
firestore_client = firestore.Client()


def extract_questions(text: str):
    """
    Split OCR text into questions using:
    Q1.
    Q2.
    Q3.
    ...
    """

    pattern = r"(Q\d+\.)"

    parts = re.split(pattern, text)

    questions = []

    i = 1
    while i < len(parts):

        question_label = parts[i].strip()

        question_text = ""

        if i + 1 < len(parts):
            question_text = parts[i + 1].strip()

        questions.append({
            "label": question_label,
            "text": question_text
        })

        i += 2

    return questions


def process_ocr_json(event, context):

    bucket_name = event["bucket"]
    file_name = event["name"]

    if not file_name.startswith("ocr-output/"):
        return

    if not file_name.endswith(".json"):
        return

    print(f"Processing OCR JSON: {file_name}")

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(file_name)

    content = blob.download_as_text()

    data = json.loads(content)

    source_file = data.get("file_name", "")

    text = data.get("text", "")

    questions = extract_questions(text)

    print(f"Questions Found: {len(questions)}")

    for index, question in enumerate(questions, start=1):

        question_id = f"JEE_Q{index}"

        firestore_client.collection(
            "jee_questions"
        ).document(question_id).set({

            "question_id": question_id,

            "question_number": index,

            "question_text": question["text"],

            "source_file": source_file,

            "created_at": datetime.utcnow()

        })

    print("Question extraction completed.")