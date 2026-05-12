import json
from pathlib import Path

QUESTIONS_PATH = Path(__file__).with_name("questions.json")

with QUESTIONS_PATH.open(encoding="utf-8") as f:
    QUESTIONS = json.load(f)
