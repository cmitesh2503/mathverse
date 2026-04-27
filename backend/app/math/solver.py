from sympy import symbols, solve, sympify

def solve_equation(expr: str):
    try:
        x = symbols('x')

        cleaned = clean_expression(expr)
        print("CLEANED EXPR:", cleaned)

        # 🔥 NO Eq() needed
        solutions = solve(sympify(cleaned), x)

        result = [float(sol) for sol in solutions]

        print("SOLVED EXPECTED:", result)

        return sorted(result)

    except Exception as e:
        print("SOLVER ERROR:", e)
        return None