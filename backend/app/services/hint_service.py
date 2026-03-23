def get_hint(level):
    hints = {
        1: "Try subtracting 3 from both sides.",
        2: "2x + 3 = 7 → 2x = 4",
        3: "Now divide both sides by 2."
    }
    return hints.get(level, "Let's solve it together.")