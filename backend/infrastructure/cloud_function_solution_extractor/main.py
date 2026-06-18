import json
import re

from google.cloud import storage
from google.cloud import firestore

storage_client = storage.Client()
firestore_client = firestore.Client()

def clean_text(text: str) -> str:

    junk_patterns = [
        r"#PaperPhodnaHai",
        r"www\.mathongo\.com",
        r"\bmathongo\b",
        r"\bmathongo\s*/\s*mathongo\b",
        r"\bmat\w*ongo\b",
        r"\b\w*mathongo\b",
        r"\bmathongo\w*\b",
        r"\bmathong\b",
        r"\bmathongs\b",
        r"\bmathon\b",
        r"\bathongo\b",
        r"\bnathongo\b",
        r"\bhongo\b",
    ]

    for pattern in junk_patterns:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE
        )

    text = re.sub(r"\s+\d+%\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b[a-z]*thongo\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"/+", " ", text)
    text = re.sub(r"%+", " ", text)
    text = re.sub(r"_+", " ", text)

    return text.strip()


def extract_solution_section(text):

    if "ANSWERS AND SOLUTIONS" not in text:
        return ""

    return text.split(
        "ANSWERS AND SOLUTIONS",
        1
    )[1]


def extract_solutions(solution_text):

    pattern = r"(\d+)\.\s*\([^)]+\)"

    matches = list(
        re.finditer(
            pattern,
            solution_text
        )
    )

    solutions = {}

    for i in range(len(matches)):

        question_no = matches[i].group(1)

        start_pos = matches[i].end()

        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(solution_text)

        solution = solution_text[start_pos:end_pos]

        solution = clean_text(solution)

        solutions[question_no] = solution

    return solutions    


def process_solutions(event, context):

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

    solution_section = extract_solution_section(text)

    if not solution_section:
        print("No solution section found")
        return

    solutions = extract_solutions(solution_section)

    print(f"Solutions Found: {len(solutions)}")

    for question_no, solution in solutions.items():

        question_id = f"JEE_Q{question_no}"

        print(
            f"Updating {question_id} -> {solution}"
        )

        firestore_client.collection(
            "jee_questions"
        ).document(question_id).set(
            {
                "solution_text": solution
            },
            merge=True
        )

    print("Solution extraction completed")