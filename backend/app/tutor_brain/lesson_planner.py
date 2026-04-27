def build_lesson_plan(rag_text: str):
    """
    Convert raw RAG content into structured teaching steps
    """

    # 🔴 TEMP simple split (later improve with LLM)
    lines = [l.strip() for l in rag_text.split("\n") if l.strip()]

    concept_steps = lines[:5]
    examples = [l for l in lines if "example" in l.lower()][:2]
    homework = lines[-3:]

    return {
        "concept_steps": lines[:5],
        "examples": lines[5:7],
        "homework": lines[-3:]
    }