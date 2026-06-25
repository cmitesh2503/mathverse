import json
import re

from google.cloud import storage
from google.cloud import firestore

storage_client = storage.Client()
firestore_client = firestore.Client()


def get_chapter(text):

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        if (
            line
            and "Questions with Answer Keys" not in line
            and "JEE Main" not in line
            and "MathonGo" not in line
        ):
            return line

    return "Unknown"


def get_exam(text):

    if "JEE Main" in text:
        return "JEE Main"

    if "JEE Advanced" in text:
        return "JEE Advanced"

    if "BITSAT" in text:
        return "BITSAT"

    return "Unknown"


def get_year(text):

    match = re.search(
        r"20\d{2}",
        text
    )

    if match:
        return int(match.group())

    return None


def get_shift(question_text):

    match = re.search(
        r"(\d{1,2}\s+[A-Za-z]+\s+Shift\s+\d)",
        question_text
    )

    if match:
        return match.group(1)

    return "Unknown"


def get_difficulty(question_text):

    length = len(question_text)

    if length < 300:
        return "Easy"

    if length < 700:
        return "Medium"

    return "Hard"

def process_metadata(event, context):

    import time
    time.sleep(20)

def process_metadata(event, context):

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

    full_text = data.get("text", "")

    chapter = get_chapter(full_text)

    exam = get_exam(full_text)

    year = get_year(full_text)

    print(f"Chapter: {chapter}")
    print(f"Exam: {exam}")
    print(f"Year: {year}")

    docs = list(firestore_client.collection(
        "jee_questions"
    ).stream())
    print(f"Total Docs Found = {len(docs)}")
    count = 0

    for doc in docs:
        print(f"Updating {doc.id}")
        question = doc.to_dict()

        question_text = question.get(
            "question_text",
            ""
        )

        shift = get_shift(
            question_text
        )

        difficulty = get_difficulty(
            question_text
        )

        firestore_client.collection(
            "jee_questions"
        ).document(
            doc.id
        ).set(
            {
                "chapter": chapter,
                "exam": exam,
                "year": year,
                "shift": shift,
                "difficulty": difficulty
            },
            merge=True
        )

        count += 1

    print(
        f"Metadata updated for {count} questions"
    )