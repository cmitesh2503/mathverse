def validate_response(response: str) -> str:

    if not response:
        return "Let's solve step by step 😊"

    # basic safety rules
    if len(response) > 1000:
        return response[:500] + "..."

    # ensure teaching tone
    if "I don't know" in response:
        return "Let's try to understand this together step by step."

    return response
