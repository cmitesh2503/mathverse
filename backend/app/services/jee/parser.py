import re


def parse_response(text):

    question = ""
    chapter = ""
    answer = ""
    solution = ""

    q = re.search(
        r"\*\*Question:\*\*(.*?)\*\*Chapter:",
        text,
        re.DOTALL
    )

    c = re.search(
        r"\*\*Chapter:\*\*(.*?)\*\*Answer:",
        text,
        re.DOTALL
    )

    a = re.search(
        r"\*\*Answer:\*\*(.*?)\*\*Solution:",
        text,
        re.DOTALL
    )

    s = re.search(
        r"\*\*Solution:\*\*(.*)",
        text,
        re.DOTALL
    )

    if q:
        question = q.group(1).strip()

    if c:
        chapter = c.group(1).strip()

    if a:
        answer = a.group(1).strip()

    if s:
        solution = s.group(1).strip()

    return {
        "question": question,
        "chapter": chapter,
        "answer": answer,
        "solution": solution
    }