import json

def load_chunks():
    with open("backend/app/data/ncert_chunks.json", "r") as f:
        return json.load(f)

def retrieve_context(topic: str):
    chunks = load_chunks()

    results = [c["text"] for c in chunks if c["topic"] == topic]

    return "\n".join(results[:2])