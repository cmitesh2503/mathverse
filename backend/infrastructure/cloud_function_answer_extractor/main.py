import json
import re

from google.cloud import storage
from google.cloud import firestore

storage_client = storage.Client()
firestore_client = firestore.Client()


def extract_answer_section(text):

    if "ANSWERS AND SOLUTIONS" not in text:
        return ""

    return text.split(
        "ANSWERS AND SOLUTIONS",
        1
    )[1]


def extract_answers(answer_text):

    pattern = r"(\d+)\.\s*\((\d+)\)"

    matches = re.findall(
        pattern,
        answer_text
    )

    answers = {}

    for question_no, answer in matches:
        answers[question_no] = answer

    return answers


def process_answers(event, context):

    bucket_name = event["bucket"]
    file_name = event["name"]

    # Process only OCR JSON files
    if not file_name.startswith("ocr-output/"):
        return

    if not file_name.endswith(".json"):
        return

    print(f"Processing OCR JSON: {file_name}")

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(file_name)

    content = blob.download_as_text()

    data = json.loads(content)

    text = data.get("text", "")

    answer_section = extract_answer_section(text)

    if not answer_section:
        print("No answer section found")
        return

    answers = extract_answers(answer_section)

    print(f"Answers Found: {len(answers)}")

    for question_no, answer in answers.items():

        question_id = f"JEE_Q{question_no}"

        print(
            f"Updating {question_id} -> {answer}"
        )

        firestore_client.collection(
            "jee_questions"
        ).document(question_id).set(
            {
                "correct_answer": answer
            },
            merge=True
        )

    print("Answer extraction completed")