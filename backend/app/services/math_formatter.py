import re

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
    
    result = text
    for symbol, word in replacements.items():
        result = result.replace(symbol, word)
        
    # Handle symbols
    result = convert_display_symbols_to_speech(result)
    
    return result