import re

_ROMAN_NUMERAL_WORDS = {
    "i": "one",
    "ii": "two",
    "iii": "three",
    "iv": "four",
    "v": "five",
    "vi": "six",
    "vii": "seven",
    "viii": "eight",
    "ix": "nine",
    "x": "ten",
}


def _convert_roman_markers_to_speech(text: str) -> str:
    """Speak exercise subparts like (iv) as numbers, not letters."""
    if not text:
        return text

    def replace_parenthesized(match: re.Match) -> str:
        roman = match.group(1).lower()
        return f"({_ROMAN_NUMERAL_WORDS.get(roman, roman)})"

    def replace_problem_suffix(match: re.Match) -> str:
        prefix = match.group(1)
        roman = match.group(2).lower()
        return f"{prefix} part {_ROMAN_NUMERAL_WORDS.get(roman, roman)}"

    result = re.sub(r"(\b\d+)\s*\(([ivx]{1,4})\)", replace_problem_suffix, text, flags=re.IGNORECASE)
    result = re.sub(r"\(([ivx]{1,4})\)", replace_parenthesized, result, flags=re.IGNORECASE)
    return result

def convert_text_to_display_symbols(text: str) -> str:
    """
    Converts text-based math notation to proper display symbols.
    Example: 'sqrt(x)' -> '√(x)', 'pi' -> 'π'
    """
    if not text:
        return text
        
    replacements = {
        "sqrt(": "√(",
        "pi": "π",
        " times ": " × ",
        " divided by ": " ÷ ",
        " degrees": "°",
        " degree": "°",
        "<=": "≤",
        ">=": "≥",
        "!=": "≠",
        "~=": "≈",
        "^2": "²",
        "^3": "³",
        " infinity": " ∞",
        " proportional to ": " ∝ ",
    }
    
    # Apply word-bounded replacements first to avoid partial matches
    result = text
    for word, symbol in replacements.items():
        # Handle space-prefixed items normally
        if word.startswith(" ") or word.endswith(" "):
            result = result.replace(word, symbol)
        else:
            # For non-spaced words like pi, sqrt(, etc., we just replace directly
            # as they are usually distinct enough
            result = result.replace(word, symbol)
            
    return result

def convert_display_symbols_to_speech(text: str) -> str:
    """
    Converts math symbols back to natural spoken words for TTS.
    Example: '√(x)' -> 'square root of x', 'π' -> 'pi'
    """
    if not text:
        return text
        
    replacements = {
        "√(": " square root of (",
        "√": " square root of ",
        "π": " pi ",
        "×": " times ",
        "÷": " divided by ",
        "°": " degrees ",
        "≤": " less than or equal to ",
        "≥": " greater than or equal to ",
        "≠": " not equal to ",
        "≈": " approximately equal to ",
        "²": " squared ",
        "³": " cubed ",
        "∞": " infinity ",
        "∝": " proportional to ",
        "∠": " angle ",
        "Δ": " triangle ",
    }
    
    result = text
    direct_replacements = {
        "√(": " square root of (",
        "√": " square root of ",
        "π": " pi ",
        "×": " times ",
        "÷": " divided by ",
        "°": " degrees ",
        "≤": " less than or equal to ",
        "≥": " greater than or equal to ",
        "≠": " not equal to ",
        "≈": " approximately equal to ",
        "²": " squared ",
        "³": " cubed ",
        "∞": " infinity ",
        "∝": " proportional to ",
        "∠": " angle ",
        "Δ": " triangle ",
    }
    for symbol, word in direct_replacements.items():
        result = result.replace(symbol, word)
    for symbol, word in replacements.items():
        result = result.replace(symbol, word)
        
    # Clean up double spaces
    result = re.sub(r"\s+", " ", result).strip()
    return result

def convert_text_to_speech(text: str) -> str:
    """
    Main pipeline: If text has text-based math, first normalize it, then convert to speech.
    """
    if not text:
        return text
        
    # Handle text-based legacy patterns
    replacements = {
        "sqrt(": " square root of (",
        "sqrt ": " square root of ",
        "~": " approximately ",
        "^2": " squared ",
        "^3": " cubed ",
        "^": " to the power of ",
    }
    
    result = _convert_roman_markers_to_speech(text)
    for symbol, word in replacements.items():
        result = result.replace(symbol, word)
        
    # Handle symbols
    result = convert_display_symbols_to_speech(result)
    
    return result
