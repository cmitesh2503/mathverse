# backend/app/agents/teacher_agent.py

def decide_mode(message: str, state: str) -> str:
    message = message.lower()

    if message.strip() in ["hi", "hello", "hey"]:
        return "GREETING"

    if any(word in message for word in ["pause", "stop", "break"]):
        return "BREAK"

    if any(word in message for word in ["don't understand", "doubt"]):
        return "DOUBT"

    return "LEARNING"

    

    # Simple rules (MVP)
    if any(word in message for word in ["don't understand", "doubt", "why", "what"]):
        return "DOUBT"

    if any(word in message for word in ["stop", "pause", "break"]):
        return "BREAK"

    return "LEARNING"