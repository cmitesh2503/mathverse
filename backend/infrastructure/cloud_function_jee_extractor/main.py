import json
import re
from datetime import datetime

from google.cloud import storage
from google.cloud import firestore

storage_client = storage.Client()
firestore_client = firestore.Client()

def clean_text(text: str) -> str:
    
    text = re.sub(
        r"\s+\d+%\s*",
        " ",
        text
    )

    # Remove MathonGo watermark variants
    text = re.sub(
        r"\b[a-z]*math[a-z]*ongo[a-z]*\b",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Remove common OCR fragments
    text = re.sub(
        r"\b(?:matl|mat|thongo|hongo|athongo|nathongo|tongo|ongo)\b",
        " ",
        text,
        flags=re.IGNORECASE
    )
    
    text = re.sub(
    r"(?i)\b(matnongo|matl|ot|tongo|1%)\b",
    " ",
    text
)
    

    # Remove branding
    text = re.sub(
        r"#PaperPhodnaHai",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"www\.mathongo\.com",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Remove repeated slashes left by OCR
    text = re.sub(r"/+", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def extract_options(question_text):

    option_matches = re.findall(
        r"\(\d\)\s*(.*?)(?=\(\d\)|$)",
        question_text,
        re.DOTALL
    )

    options = [
        clean_text(option)
        for option in option_matches
    ]

    if len(option_matches) == 0:
        return question_text, []

    question_only = re.split(
        r"\(\d\)",
        question_text,
        maxsplit=1
    )[0]

    return question_only.strip(), options
    

def extract_questions(text: str):

    text = text.split("ANSWERS AND SOLUTIONS")[0]
    text = clean_text(text)
    pattern = r"(Q\d+\.)"
    parts = re.split(pattern, text)

    questions = []

    i = 1

    while i < len(parts):

        question_label = parts[i].strip()

        question_text = ""

        if i + 1 < len(parts):
            question_text = parts[i + 1].strip()

        question_text = clean_text(question_text)

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
        question_text, options = extract_options(
            question["text"]
        )
        print(f"Question {index}")
    
        
        firestore_client.collection(
            "jee_questions"
        ).document(question_id).set({

            "question_id": question_id,

            "question_number": index,

            "question_text": question_text,

            "options": options,

            "source_file": source_file,

            "created_at": datetime.utcnow()

        })

    print("Question extraction completed.")