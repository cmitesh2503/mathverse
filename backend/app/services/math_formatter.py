"""
Math symbol formatting utilities for display and speech synthesis.
Converts between text representations and proper mathematical symbols.
"""

import re
from typing import Dict, Tuple

# Symbol mappings: (text_pattern, display_symbol, speech_text)
MATH_SYMBOLS = [
    # Square root variations
    (r'\bsqrt\s*\(\s*([^)]+)\s*\)', r'√(\1)', 'square root'),
    (r'\bsqrt\b', '√', 'square root'),
    (r'√', '√', 'square root'),
    
    # Pi variations
    (r'\bpi\b', 'π', 'pi'),
    (r'π', 'π', 'pi'),
    
    # Multiplication
    (r'\bx\s+', '× ', 'times'),  # "x " to avoid matching variable x
    (r'\btimes\b', '×', 'times'),
    (r'×', '×', 'times'),
    
    # Division
    (r'\bdivided\s+by\b', '÷', 'divided by'),
    (r'\bdiv\b', '÷', 'divided by'),
    (r'÷', '÷', 'divided by'),
    
    # Degrees
    (r'\bdegrees\b', '°', 'degrees'),
    (r'\b°\b', '°', 'degrees'),
    
    # Inequality symbols
    (r'\bless\s+than\s+or\s+equal\s+to\b', '≤', 'less than or equal to'),
    (r'\b<=\b', '≤', 'less than or equal to'),
    (r'≤', '≤', 'less than or equal to'),
    
    (r'\bgreater\s+than\s+or\s+equal\s+to\b', '≥', 'greater than or equal to'),
    (r'\b>=\b', '≥', 'greater than or equal to'),
    (r'≥', '≥', 'greater than or equal to'),
    
    (r'\bnot\s+equal\s+to\b', '≠', 'not equal to'),
    (r'\b!=\b', '≠', 'not equal to'),
    (r'≠', '≠', 'not equal to'),
    
    # Approximately equal
    (r'\bapproximately\s+equal\s+to\b', '≈', 'approximately equal to'),
    (r'\b~=\b', '≈', 'approximately equal to'),
    (r'≈', '≈', 'approximately equal to'),
    
    (r'\b~\b', '≈', 'approximately'),
    
    # Powers and exponents
    (r'\^2\b', '²', 'squared'),
    (r'\^3\b', '³', 'cubed'),
    (r'\^', '^', 'to the power of'),
    
    # Fractions (partial, more complex handling needed)
    (r'/', '/', 'over'),
    
    # Infinity
    (r'\binfinity\b', '∞', 'infinity'),
    (r'∞', '∞', 'infinity'),
    
    # Proportional
    (r'\bproportional\b', '∝', 'proportional to'),
    (r'∝', '∝', 'proportional to'),
]


def convert_text_to_display_symbols(text: str) -> str:
    """
    Convert text-based math notation to display symbols.
    Example: "sqrt(x)" → "√(x)", "pi" → "π"
    """
    if not text:
        return text
    
    result = text
    
    # Sqrt patterns - handle with group replacement
    result = re.sub(r'\bsqrt\s*\(\s*([^)]+)\s*\)', r'√(\1)', result, flags=re.IGNORECASE)
    result = re.sub(r'\bsqrt\b', '√', result, flags=re.IGNORECASE)
    
    # Pi
    result = re.sub(r'\bpi\b', 'π', result, flags=re.IGNORECASE)
    
    # Multiplication (be careful with "x" variable)
    # Only replace when it's a standalone word
    result = re.sub(r'\btimes\b', '×', result, flags=re.IGNORECASE)
    result = re.sub(r'\bmultiply\s+by\b', '×', result, flags=re.IGNORECASE)
    
    # Division
    result = re.sub(r'\bdivided\s+by\b', '÷', result, flags=re.IGNORECASE)
    result = re.sub(r'\bdiv\b', '÷', result, flags=re.IGNORECASE)
    
    # Degrees
    result = re.sub(r'\bdegrees\b', '°', result, flags=re.IGNORECASE)
    
    # Inequalities
    result = re.sub(r'\bless\s+than\s+or\s+equal\s+to\b', '≤', result, flags=re.IGNORECASE)
    result = re.sub(r'\b<=\b', '≤', result, flags=re.IGNORECASE)
    
    result = re.sub(r'\bgreater\s+than\s+or\s+equal\s+to\b', '≥', result, flags=re.IGNORECASE)
    result = re.sub(r'\b>=\b', '≥', result, flags=re.IGNORECASE)
    
    result = re.sub(r'\bnot\s+equal\s+to\b', '≠', result, flags=re.IGNORECASE)
    result = re.sub(r'\b!=\b', '≠', result, flags=re.IGNORECASE)
    
    # Approximately
    result = re.sub(r'\bapproximately\s+equal\s+to\b', '≈', result, flags=re.IGNORECASE)
    result = re.sub(r'\b~=\b', '≈', result, flags=re.IGNORECASE)
    
    # Infinity
    result = re.sub(r'\binfinity\b', '∞', result, flags=re.IGNORECASE)
    
    # Proportional
    result = re.sub(r'\bproportional\s+to\b', '∝', result, flags=re.IGNORECASE)
    
    # Powers (must be careful)
    result = result.replace('^2', '²')
    result = result.replace('^3', '³')
    result = result.replace('^4', '⁴')
    
    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result)
    
    return result.strip()


def convert_display_symbols_to_speech(text: str) -> str:
    """
    Convert mathematical display symbols to spoken language.
    Example: "√x" → "square root of x", "π" → "pi"
    """
    if not text:
        return text
    
    result = text
    
    # Square root with parentheses: √(x) → square root of x
    result = re.sub(r'√\s*\(\s*([^)]+)\s*\)', r'square root of \1', result)
    # Square root: √x → square root of x
    result = re.sub(r'√\s*(\S+)', r'square root of \1', result)
    # Fallback
    result = result.replace('√', 'square root of ')
    
    # Pi
    result = re.sub(r'π', 'pi', result, flags=re.IGNORECASE)
    
    # Multiplication
    result = result.replace('×', ' times ')
    
    # Division
    result = result.replace('÷', ' divided by ')
    
    # Degrees
    result = result.replace('°', ' degrees ')
    
    # Inequalities
    result = result.replace('≤', ' less than or equal to ')
    result = result.replace('≥', ' greater than or equal to ')
    result = result.replace('≠', ' not equal to ')
    
    # Approximately
    result = result.replace('≈', ' approximately equal to ')
    
    # Infinity
    result = result.replace('∞', ' infinity ')
    
    # Proportional
    result = result.replace('∝', ' proportional to ')
    
    # Powers
    result = result.replace('²', ' squared ')
    result = result.replace('³', ' cubed ')
    result = result.replace('^', ' to the power of ')
    
    # Clean up spaces
    result = re.sub(r'\s+', ' ', result)
    
    return result.strip()


def convert_text_to_speech(text: str) -> str:
    """
    Convert text-based math notation directly to spoken language.
    This is a combined operation: text → symbols → speech
    """
    # First convert text to display symbols
    with_symbols = convert_text_to_display_symbols(text)
    # Then convert symbols to speech
    spoken = convert_display_symbols_to_speech(with_symbols)
    return spoken


def extract_math_symbols_from_text(text: str) -> set[str]:
    """Extract all math symbols found in text."""
    symbols = set()
    math_symbol_patterns = {
        '√': 'sqrt',
        'π': 'pi',
        '×': 'times',
        '÷': 'divided',
        '°': 'degrees',
        '≤': 'lte',
        '≥': 'gte',
        '≠': 'neq',
        '≈': 'approx',
        '∞': 'infinity',
        '∝': 'proportional',
    }
    
    for symbol in math_symbol_patterns:
        if symbol in text:
            symbols.add(symbol)
    
    return symbols


def annotate_math_symbols(text: str, wrap_char: str = '*') -> str:
    """
    Wrap mathematical symbols for special handling.
    Example: with wrap_char='*': "√" becomes "*√*"
    """
    math_symbols = {
        '√', 'π', '×', '÷', '°', '≤', '≥', '≠', '≈', '∞', '∝',
        '²', '³', '⁴'
    }
    
    result = text
    for symbol in math_symbols:
        result = result.replace(symbol, f'{wrap_char}{symbol}{wrap_char}')
    
    return result
