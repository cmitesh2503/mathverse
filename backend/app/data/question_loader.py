import json

with open("backend/app/data/questions.json") as f:
    QUESTIONS = json.load(f)