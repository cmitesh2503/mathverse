# backend/app/agents/teacher_agent.py

def decide_mode(message: str, lesson_state: str) -> str:
    """
    Decide how tutor should react to student input
    """

    message = message.lower()

    # Simple rules (MVP)
    if any(word in message for word in ["don't understand", "doubt", "why", "what"]):
        return "DOUBT"

    if any(word in message for word in ["stop", "pause", "break"]):
        return "BREAK"

    return "LEARNING"