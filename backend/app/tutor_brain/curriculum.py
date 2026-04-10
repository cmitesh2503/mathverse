from __future__ import annotations


GRADE_CURRICULUM = {
    9: {
        "board": "CBSE",
        "subject": "Mathematics",
        "default_topic_slug": "linear_equations_in_two_variables",
        "chapters": [
            {
                "slug": "number_systems",
                "title": "Number Systems",
                "summary": "Real numbers, irrational numbers, and decimal expansions.",
                "aliases": ["number systems", "real numbers"],
            },
            {
                "slug": "polynomials",
                "title": "Polynomials",
                "summary": "Terms, coefficients, identities, and factorisation ideas.",
                "aliases": ["polynomials"],
            },
            {
                "slug": "coordinate_geometry",
                "title": "Coordinate Geometry",
                "summary": "Cartesian plane, axes, and plotting ordered pairs.",
                "aliases": ["coordinate geometry", "coordinates"],
            },
            {
                "slug": "linear_equations_in_two_variables",
                "title": "Linear Equations in Two Variables",
                "summary": "Understanding equations in x and y, ordered pairs, and graphs.",
                "aliases": ["linear equations", "two variables", "linear equations in two variables"],
                "teaching_anchor": (
                    "A linear equation in two variables can be written as ax + by + c = 0, "
                    "where a and b are not both zero."
                ),
                "classroom_goal": "Students should recognise solutions as ordered pairs and connect equations to straight lines.",
                "concepts": [
                    {
                        "id": "form_and_solution",
                        "title": "Form of a Linear Equation",
                        "explanation": (
                            "A linear equation in two variables contains x and y only to the first power. "
                            "Any ordered pair that makes the equation true is called a solution."
                        ),
                        "board_work": [
                            "Example: x + y = 7",
                            "If x = 2, then y = 5 gives a true statement because 2 + 5 = 7.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "If x = 2 in x + y = 7, what is y?",
                                "answer_type": "number",
                                "answer": 5,
                                "hint": "Substitute x = 2 first, then solve for y.",
                                "steps": [
                                    "Write the equation x + y = 7.",
                                    "Replace x with 2 so 2 + y = 7.",
                                    "Subtract 2 from both sides to get y = 5.",
                                ],
                            },
                            {
                                "prompt": "For 2x + y = 6, find y when x = 1.",
                                "answer_type": "number",
                                "answer": 4,
                                "hint": "Put x = 1 into the equation and simplify.",
                                "steps": [
                                    "Substitute x = 1 into 2x + y = 6.",
                                    "This gives 2(1) + y = 6, so 2 + y = 6.",
                                    "Subtract 2 from both sides to get y = 4.",
                                ],
                            },
                        ],
                    },
                    {
                        "id": "graphing_pairs",
                        "title": "Ordered Pairs and Graphs",
                        "explanation": (
                            "Each solution of a linear equation corresponds to a point on a graph. "
                            "Plotting multiple solutions gives a straight line."
                        ),
                        "board_work": [
                            "Equation: x + y = 4",
                            "Solutions: (1, 3), (2, 2), (3, 1)",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Does the ordered pair (1, 3) satisfy x + y = 4? Answer yes or no.",
                                "answer_type": "text",
                                "answer": "yes",
                                "accepted_answers": ["yes", "y"],
                                "hint": "Add the x-coordinate and y-coordinate.",
                                "steps": [
                                    "Replace x with 1 and y with 3.",
                                    "Compute 1 + 3.",
                                    "Since the result is 4, the pair is a solution.",
                                ],
                            }
                        ],
                    },
                ],
            },
            {
                "slug": "euclids_geometry",
                "title": "Introduction to Euclid's Geometry",
                "summary": "Axioms, postulates, and the logic of geometry.",
                "aliases": ["euclid", "geometry"],
            },
            {
                "slug": "lines_and_angles",
                "title": "Lines and Angles",
                "summary": "Angle relationships, transversals, and parallel lines.",
                "aliases": ["lines and angles", "angles"],
            },
            {
                "slug": "triangles",
                "title": "Triangles",
                "summary": "Congruence, angle sum property, and triangle inequalities.",
                "aliases": ["triangles"],
            },
            {
                "slug": "quadrilaterals",
                "title": "Quadrilaterals",
                "summary": "Properties of quadrilaterals and angle relationships.",
                "aliases": ["quadrilaterals"],
            },
            {
                "slug": "areas_of_parallelograms_and_triangles",
                "title": "Areas of Parallelograms and Triangles",
                "summary": "Area relationships using common bases and equal heights.",
                "aliases": ["areas of parallelograms", "triangles area"],
            },
            {
                "slug": "circles",
                "title": "Circles",
                "summary": "Angles and chords in circles.",
                "aliases": ["circles"],
            },
            {
                "slug": "constructions",
                "title": "Constructions",
                "summary": "Basic ruler-and-compass geometric constructions.",
                "aliases": ["constructions"],
            },
            {
                "slug": "herons_formula",
                "title": "Heron's Formula",
                "summary": "Area of a triangle using side lengths.",
                "aliases": ["heron's formula", "herons formula"],
            },
            {
                "slug": "surface_areas_and_volumes",
                "title": "Surface Areas and Volumes",
                "summary": "Area and volume of solids such as cylinders and cones.",
                "aliases": ["surface area", "volume"],
            },
            {
                "slug": "statistics",
                "title": "Statistics",
                "summary": "Collecting, organising, and representing data.",
                "aliases": ["statistics"],
            },
            {
                "slug": "probability",
                "title": "Probability",
                "summary": "Experimental probability and simple events.",
                "aliases": ["probability"],
            },
        ],
    },
    10: {
        "board": "CBSE",
        "subject": "Mathematics",
        "default_topic_slug": "real_numbers",
        "chapters": [
            {
                "slug": "real_numbers",
                "title": "Real Numbers",
                "summary": "Euclid's division lemma, HCF, irrational numbers, and decimal expansions.",
                "aliases": ["real numbers"],
                "teaching_anchor": (
                    "For any two positive integers a and b, Euclid's division lemma says "
                    "a = bq + r, where 0 <= r < b."
                ),
                "classroom_goal": (
                    "Students should use Euclid's division lemma for HCF questions and explain "
                    "why decimal expansions of rational numbers either terminate or repeat."
                ),
                "book_topics": [
                    "Euclid's Division Lemma",
                    "Revisiting HCF and LCM",
                    "Decimal Expansions of Rational Numbers",
                    "Irrational Numbers",
                ],
                "homework": [
                    "Use Euclid's division lemma to find the HCF of 135 and 225.",
                    "State whether 13/160 has a terminating decimal expansion and explain why.",
                    "Write two examples each of rational and irrational numbers.",
                ],
                "concepts": [
                    {
                        "id": "euclid_division_lemma",
                        "title": "Euclid's Division Lemma",
                        "definition": "For any two positive integers a and b, there exist whole numbers q and r such that a = bq + r, where 0 <= r < b.",
                        "explanation": (
                            "Euclid's division lemma helps us break one number into divisor, quotient, "
                            "and remainder. It is the starting point for many HCF problems."
                        ),
                        "board_work": [
                            "Dividend = Divisor × Quotient + Remainder",
                            "26 = 5 × 5 + 1",
                            "The remainder must always be smaller than the divisor.",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "Using Euclid's division lemma, write 37 in the form 5q + r. What are q and r?",
                                "answer_type": "pair",
                                "answer": [7, 2],
                                "answer_labels": ["q", "r"],
                                "rule_used": "Euclid's division lemma",
                                "hint": "Divide 37 by 5. The quotient is the whole-number part and the remainder is what is left.",
                                "steps": [
                                    "Divide 37 by 5.",
                                    "We get quotient 7 because 5 x 7 = 35.",
                                    "The remainder is 37 - 35 = 2, so 37 = 5 x 7 + 2.",
                                ],
                            },
                            {
                                "prompt": "Using Euclid's division lemma, write 52 in the form 7q + r. What are q and r?",
                                "answer_type": "pair",
                                "answer": [7, 3],
                                "answer_labels": ["q", "r"],
                                "rule_used": "Euclid's division lemma",
                                "hint": "Divide 52 by 7 and write the quotient and remainder.",
                                "steps": [
                                    "Divide 52 by 7.",
                                    "We get quotient 7 because 7 x 7 = 49.",
                                    "The remainder is 52 - 49 = 3, so 52 = 7 x 7 + 3.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Write 63 in the form 8q + r. What are q and r?",
                                "answer_type": "pair",
                                "answer": [7, 7],
                                "answer_labels": ["q", "r"],
                                "rule_used": "Euclid's division lemma",
                                "hint": "Find the quotient when 63 is divided by 8.",
                                "steps": [
                                    "Divide 63 by 8.",
                                    "We get quotient 7 because 8 x 7 = 56.",
                                    "The remainder is 63 - 56 = 7, so 63 = 8 x 7 + 7.",
                                ],
                            },
                            {
                                "prompt": "Write 125 in the form 9q + r. What are q and r?",
                                "answer_type": "pair",
                                "answer": [13, 8],
                                "answer_labels": ["q", "r"],
                                "rule_used": "Euclid's division lemma",
                                "hint": "Use quotient 13 first and then compute the remainder.",
                                "steps": [
                                    "Divide 125 by 9.",
                                    "We get quotient 13 because 9 x 13 = 117.",
                                    "The remainder is 125 - 117 = 8, so 125 = 9 x 13 + 8.",
                                ],
                            },
                        ],
                        "homework": [
                            "Write 46 in the form 6q + r.",
                            "Write 81 in the form 11q + r.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Using Euclid's division lemma, write 37 in the form 5q + r. What are q and r?",
                                "answer_type": "pair",
                                "answer": [7, 2],
                                "answer_labels": ["q", "r"],
                                "hint": "Divide 37 by 5. The quotient is the whole-number part and the remainder is what is left.",
                                "steps": [
                                    "Divide 37 by 5.",
                                    "We get quotient 7 because 5 × 7 = 35.",
                                    "The remainder is 37 - 35 = 2, so 37 = 5 × 7 + 2.",
                                ],
                            }
                        ],
                    },
                    {
                        "id": "hcf_by_euclid_algorithm",
                        "title": "Finding HCF by Euclid's Algorithm",
                        "explanation": (
                            "We repeatedly apply Euclid's division lemma until the remainder becomes zero. "
                            "The last non-zero divisor is the HCF."
                        ),
                        "board_work": [
                            "455 = 42 × 10 + 35",
                            "42 = 35 × 1 + 7",
                            "35 = 7 × 5 + 0",
                            "So HCF(455, 42) = 7",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "Find the HCF of 65 and 40.",
                                "answer_type": "number",
                                "answer": 5,
                                "method": "Use Euclid's algorithm and keep dividing until the remainder becomes zero",
                                "hint": "Use repeated division until the remainder becomes zero.",
                                "steps": [
                                    "Divide 65 by 40 to get 65 = 40 x 1 + 25.",
                                    "Now divide 40 by 25 to get 40 = 25 x 1 + 15.",
                                    "Divide 25 by 15 to get 25 = 15 x 1 + 10.",
                                    "Divide 15 by 10 to get 15 = 10 x 1 + 5.",
                                    "Divide 10 by 5 to get 10 = 5 x 2 + 0, so the HCF is 5.",
                                ],
                            },
                            {
                                "prompt": "Find the HCF of 135 and 225.",
                                "answer_type": "number",
                                "answer": 45,
                                "method": "Use Euclid's algorithm and stop at the first zero remainder",
                                "hint": "Start by dividing the larger number by the smaller number.",
                                "steps": [
                                    "Divide 225 by 135 to get 225 = 135 x 1 + 90.",
                                    "Now divide 135 by 90 to get 135 = 90 x 1 + 45.",
                                    "Divide 90 by 45 to get 90 = 45 x 2 + 0.",
                                    "The last non-zero divisor is 45, so HCF(135, 225) = 45.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Find the HCF of 867 and 255.",
                                "answer_type": "number",
                                "answer": 51,
                                "method": "Use Euclid's algorithm",
                                "hint": "Keep dividing until the remainder becomes zero.",
                                "steps": [
                                    "Divide 867 by 255 to get 867 = 255 x 3 + 102.",
                                    "Now divide 255 by 102 to get 255 = 102 x 2 + 51.",
                                    "Divide 102 by 51 to get 102 = 51 x 2 + 0.",
                                    "The last non-zero divisor is 51, so the HCF is 51.",
                                ],
                            },
                            {
                                "prompt": "Find the HCF of 96 and 404.",
                                "answer_type": "number",
                                "answer": 4,
                                "method": "Use Euclid's algorithm",
                                "hint": "Start by dividing 404 by 96.",
                                "steps": [
                                    "Divide 404 by 96 to get 404 = 96 x 4 + 20.",
                                    "Now divide 96 by 20 to get 96 = 20 x 4 + 16.",
                                    "Divide 20 by 16 to get 20 = 16 x 1 + 4.",
                                    "Divide 16 by 4 to get 16 = 4 x 4 + 0.",
                                    "The last non-zero divisor is 4, so the HCF is 4.",
                                ],
                            },
                        ],
                        "homework": [
                            "Find the HCF of 184 and 69 by Euclid's algorithm.",
                            "Find the HCF of 196 and 38220 by Euclid's algorithm.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Find the HCF of 65 and 40.",
                                "answer_type": "number",
                                "answer": 5,
                                "hint": "Use repeated division until the remainder becomes zero.",
                                "steps": [
                                    "Divide 65 by 40 to get 65 = 40 × 1 + 25.",
                                    "Now divide 40 by 25 to get 40 = 25 × 1 + 15.",
                                    "Divide 25 by 15 to get 25 = 15 × 1 + 10.",
                                    "Divide 15 by 10 to get 15 = 10 × 1 + 5.",
                                    "Divide 10 by 5 to get 10 = 5 × 2 + 0, so the HCF is 5.",
                                ],
                            }
                        ],
                    },
                    {
                        "id": "decimal_expansion_and_irrationals",
                        "title": "Decimal Expansions and Irrational Numbers",
                        "definition": "A rational number has a terminating or repeating decimal expansion, while an irrational number has a non-terminating, non-repeating decimal expansion.",
                        "explanation": (
                            "A rational number has a decimal expansion that either terminates or repeats. "
                            "An irrational number has a non-terminating, non-repeating decimal expansion."
                        ),
                        "board_work": [
                            "1/8 = 0.125 terminates",
                            "1/3 = 0.333... repeats",
                            "√2 = 1.4142... is non-terminating and non-repeating",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "Does 1/8 have a terminating decimal expansion? Answer yes or no.",
                                "answer_type": "text",
                                "answer": "yes",
                                "accepted_answers": ["yes", "y"],
                                "rule_used": "A rational number terminates when its denominator has only 2s and 5s after simplification",
                                "hint": "Convert the fraction to decimal or think about powers of 2 and 5 in the denominator.",
                                "steps": [
                                    "Write 1 / 8.",
                                    "This gives 0.125, which ends after three decimal places.",
                                    "So the decimal expansion is terminating.",
                                ],
                            },
                            {
                                "prompt": "Does 13/3125 have a terminating decimal expansion? Answer yes or no.",
                                "answer_type": "text",
                                "answer": "yes",
                                "accepted_answers": ["yes", "y"],
                                "rule_used": "A rational number terminates when the denominator has only factors 2 and 5 after simplification",
                                "hint": "Write 3125 as a power of 5.",
                                "steps": [
                                    "Observe that 3125 = 5 x 5 x 5 x 5 x 5 = 5^5.",
                                    "The denominator has only the prime factor 5.",
                                    "So 13/3125 has a terminating decimal expansion.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Will 7/30 have a terminating decimal expansion? Answer yes or no.",
                                "answer_type": "text",
                                "answer": "no",
                                "accepted_answers": ["no", "n"],
                                "rule_used": "A rational number repeats when the simplified denominator has a prime factor other than 2 or 5",
                                "hint": "Factorise 30 first.",
                                "steps": [
                                    "Factorise 30 as 2 x 3 x 5.",
                                    "The denominator contains 3, which is neither 2 nor 5.",
                                    "So 7/30 does not terminate. Its decimal expansion is non-terminating recurring.",
                                ],
                            },
                            {
                                "prompt": "Is sqrt(2) rational or irrational?",
                                "answer_type": "text",
                                "answer": "irrational",
                                "accepted_answers": ["irrational"],
                                "rule_used": "An irrational number has a non-terminating, non-repeating decimal expansion",
                                "hint": "Think about the decimal expansion of sqrt(2).",
                                "steps": [
                                    "The decimal expansion of sqrt(2) goes on without ending.",
                                    "It also does not repeat in a fixed pattern.",
                                    "So sqrt(2) is irrational.",
                                ],
                            },
                        ],
                        "homework": [
                            "State whether 17/200 has a terminating decimal expansion and explain why.",
                            "State whether 29/75 has a terminating decimal expansion and explain why.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Does 1/8 have a terminating decimal expansion? Answer yes or no.",
                                "answer_type": "text",
                                "answer": "yes",
                                "accepted_answers": ["yes", "y"],
                                "hint": "Convert the fraction to decimal or think about powers of 2 and 5 in the denominator.",
                                "steps": [
                                    "Write 1 ÷ 8.",
                                    "This gives 0.125, which ends after three decimal places.",
                                    "So the decimal expansion is terminating.",
                                ],
                            }
                        ],
                    },
                ],
            },
            {
                "slug": "polynomials",
                "title": "Polynomials",
                "summary": "Zeros of polynomials and relations with coefficients.",
                "aliases": ["polynomials"],
                "teaching_anchor": (
                    "A polynomial is an algebraic expression formed using variables with whole-number powers."
                ),
                "classroom_goal": (
                    "Students should identify the zeroes of simple polynomials and connect the zeroes "
                    "with the coefficients in quadratic polynomials."
                ),
                "book_topics": [
                    "Geometrical Meaning of Zeroes",
                    "Relationship between Zeroes and Coefficients",
                    "Division Algorithm for Polynomials",
                ],
                "homework": [
                    "Find the zeroes of x^2 - 5x + 6.",
                    "For x^2 + 7x + 12, write the sum and product of the zeroes.",
                    "Verify the division algorithm for p(x) = x^2 - 1 and g(x) = x - 1.",
                ],
                "concepts": [
                    {
                        "id": "zeroes_of_polynomial",
                        "title": "Zeroes of a Polynomial",
                        "definition": "A zero of a polynomial is a value of x for which the polynomial becomes zero.",
                        "explanation": (
                            "A zero of a polynomial is a value of x that makes the polynomial equal to zero. "
                            "On a graph, the zeroes are the x-coordinates where the curve meets the x-axis."
                        ),
                        "board_work": [
                            "p(x) = x^2 - 5x + 6",
                            "p(2) = 0 and p(3) = 0",
                            "So the zeroes are 2 and 3",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "Find one zero of p(x) = x^2 - 4.",
                                "answer_type": "number",
                                "answer": 2,
                                "method": "Set the polynomial equal to zero and solve",
                                "hint": "Set x^2 - 4 = 0 and solve for x.",
                                "steps": [
                                    "Write x^2 - 4 = 0.",
                                    "This gives x^2 = 4.",
                                    "Taking the positive value gives one zero as x = 2.",
                                ],
                            },
                            {
                                "prompt": "Find the zeroes of p(x) = x^2 - 5x + 6.",
                                "answer_type": "text",
                                "answer": "2 and 3",
                                "accepted_answers": ["2,3", "3,2", "2 and 3", "3 and 2"],
                                "method": "Factorise the quadratic polynomial",
                                "hint": "Split the middle term of x^2 - 5x + 6.",
                                "steps": [
                                    "Factorise x^2 - 5x + 6 as (x - 2)(x - 3).",
                                    "Set each factor equal to zero.",
                                    "So x = 2 and x = 3 are the zeroes.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Find the zeroes of p(x) = x^2 - 7x + 12.",
                                "answer_type": "text",
                                "answer": "3 and 4",
                                "accepted_answers": ["3,4", "4,3", "3 and 4", "4 and 3"],
                                "method": "Factorise the quadratic polynomial",
                                "hint": "Look for two numbers whose product is 12 and sum is 7.",
                                "steps": [
                                    "Factorise x^2 - 7x + 12 as (x - 3)(x - 4).",
                                    "Set each factor equal to zero.",
                                    "So the zeroes are 3 and 4.",
                                ],
                            },
                            {
                                "prompt": "Find one zero of p(x) = x^2 - 9.",
                                "answer_type": "number",
                                "answer": 3,
                                "method": "Use difference of squares",
                                "hint": "Write x^2 - 9 as x^2 - 3^2.",
                                "steps": [
                                    "Write x^2 - 9 = 0.",
                                    "This gives x^2 = 9.",
                                    "Taking the positive value gives one zero as x = 3.",
                                ],
                            },
                        ],
                        "homework": [
                            "Find the zeroes of x^2 - 6x + 8.",
                            "Find one zero of x^2 - 16.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Find one zero of p(x) = x^2 - 4.",
                                "answer_type": "number",
                                "answer": 2,
                                "hint": "Set x^2 - 4 = 0 and solve for x.",
                                "steps": [
                                    "Write x^2 - 4 = 0.",
                                    "This gives x^2 = 4.",
                                    "Taking the positive value gives one zero as x = 2.",
                                ],
                            }
                        ],
                    },
                    {
                        "id": "relation_with_coefficients",
                        "title": "Relationship between Zeroes and Coefficients",
                        "definition": "For ax^2 + bx + c, the sum of the zeroes is -b/a and the product of the zeroes is c/a.",
                        "explanation": (
                            "For a quadratic polynomial ax^2 + bx + c, the sum of the zeroes is -b/a and "
                            "the product of the zeroes is c/a."
                        ),
                        "board_work": [
                            "For x^2 - 5x + 6, a = 1, b = -5, c = 6",
                            "Sum of zeroes = -(-5)/1 = 5",
                            "Product of zeroes = 6/1 = 6",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "For x^2 - 7x + 10, what is the sum of the zeroes?",
                                "answer_type": "number",
                                "answer": 7,
                                "theorem_used": "For ax^2 + bx + c, sum of zeroes = -b/a",
                                "hint": "Use the formula -b/a.",
                                "steps": [
                                    "Compare x^2 - 7x + 10 with ax^2 + bx + c.",
                                    "Here a = 1 and b = -7.",
                                    "So the sum of the zeroes is -(-7)/1 = 7.",
                                ],
                            },
                            {
                                "prompt": "For x^2 - 7x + 10, what is the product of the zeroes?",
                                "answer_type": "number",
                                "answer": 10,
                                "theorem_used": "For ax^2 + bx + c, product of zeroes = c/a",
                                "hint": "Use the formula c/a.",
                                "steps": [
                                    "Compare x^2 - 7x + 10 with ax^2 + bx + c.",
                                    "Here a = 1 and c = 10.",
                                    "So the product of the zeroes is 10/1 = 10.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "For 2x^2 - 5x + 3, what is the sum of the zeroes?",
                                "answer_type": "number",
                                "answer": 2.5,
                                "theorem_used": "For ax^2 + bx + c, sum of zeroes = -b/a",
                                "hint": "Compare the polynomial with ax^2 + bx + c.",
                                "steps": [
                                    "For 2x^2 - 5x + 3, we have a = 2 and b = -5.",
                                    "Use the relation sum of zeroes = -b/a.",
                                    "So the sum is -(-5)/2 = 5/2.",
                                ],
                            },
                            {
                                "prompt": "For 2x^2 - 5x + 3, what is the product of the zeroes?",
                                "answer_type": "number",
                                "answer": 1.5,
                                "theorem_used": "For ax^2 + bx + c, product of zeroes = c/a",
                                "hint": "Use c/a for the product.",
                                "steps": [
                                    "For 2x^2 - 5x + 3, we have a = 2 and c = 3.",
                                    "Use the relation product of zeroes = c/a.",
                                    "So the product is 3/2.",
                                ],
                            },
                        ],
                        "homework": [
                            "For x^2 + 9x + 14, write the sum and product of the zeroes.",
                            "For 3x^2 - x - 4, write the sum and product of the zeroes.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "For x^2 - 7x + 10, what is the sum of the zeroes?",
                                "answer_type": "number",
                                "answer": 7,
                                "hint": "Use the formula -b/a.",
                                "steps": [
                                    "Compare x^2 - 7x + 10 with ax^2 + bx + c.",
                                    "Here a = 1 and b = -7.",
                                    "So the sum of the zeroes is -(-7)/1 = 7.",
                                ],
                            }
                        ],
                    },
                ],
            },
            {
                "slug": "pair_of_linear_equations_in_two_variables",
                "title": "Pair of Linear Equations in Two Variables",
                "summary": "Solving simultaneous linear equations graphically and algebraically.",
                "aliases": ["pair of linear equations", "simultaneous equations", "linear equations"],
                "teaching_anchor": (
                    "A pair of linear equations in two variables can have one solution, no solution, "
                    "or infinitely many solutions depending on the lines they represent."
                ),
                "classroom_goal": "Students should solve pairs of equations using substitution or elimination and interpret the result graphically.",
                "book_topics": [
                    "What a Pair of Equations Represents",
                    "Graphical Method",
                    "Substitution Method",
                    "Elimination Method",
                ],
                "homework": [
                    "Solve x + y = 5 and x - y = 1.",
                    "Solve 2x + y = 11 and x + y = 7.",
                    "State whether the pair 2x + y = 4 and 4x + 2y = 8 has one solution, no solution, or infinitely many solutions.",
                ],
                "concepts": [
                    {
                        "id": "graphical_meaning",
                        "title": "What a Pair of Equations Represents",
                        "definition": "Each linear equation represents a straight line, and the common solution is their intersection point.",
                        "explanation": (
                            "Each linear equation represents a straight line. "
                            "The common solution of two equations is the point where the two lines intersect."
                        ),
                        "board_work": [
                            "x + y = 3 and x - y = 1",
                            "The solution is the point that satisfies both equations at once.",
                        ],
                        "graph": {
                            "x_min": 0,
                            "x_max": 4,
                            "y_min": 0,
                            "y_max": 4,
                            "lines": [
                                {
                                    "label": "x + y = 3",
                                    "color": "#60a5fa",
                                    "points": [[0, 3], [3, 0]],
                                },
                                {
                                    "label": "x - y = 1",
                                    "color": "#f59e0b",
                                    "points": [[1, 0], [4, 3]],
                                },
                            ],
                            "points": [
                                {
                                    "x": 2,
                                    "y": 1,
                                    "label": "(2, 1)",
                                    "color": "#fef08a",
                                }
                            ],
                        },
                        "ncert_examples": [
                            {
                                "prompt": "Solve x + y = 3 and x - y = 1. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 1],
                                "method": "Use elimination by adding the two equations",
                                "hint": "Add the two equations first to eliminate y.",
                                "steps": [
                                    "Add the equations: (x + y) + (x - y) = 3 + 1.",
                                    "This gives 2x = 4, so x = 2.",
                                    "Substitute x = 2 into x + y = 3 to get y = 1.",
                                ],
                            },
                            {
                                "prompt": "Solve x + y = 5 and x - y = 1. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [3, 2],
                                "method": "Use elimination by adding the two equations",
                                "hint": "Add the equations to remove y.",
                                "steps": [
                                    "Add the equations: (x + y) + (x - y) = 5 + 1.",
                                    "This gives 2x = 6, so x = 3.",
                                    "Substitute x = 3 into x + y = 5 to get y = 2.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Solve 2x + y = 7 and x + y = 5. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 3],
                                "method": "Use elimination by subtracting the second equation from the first",
                                "hint": "Subtract the second equation from the first.",
                                "steps": [
                                    "Subtract x + y = 5 from 2x + y = 7.",
                                    "This gives x = 2.",
                                    "Substitute x = 2 into x + y = 5 to get y = 3.",
                                ],
                            },
                        ],
                        "homework": [
                            "Solve 3x + y = 11 and x + y = 7.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Solve x + y = 3 and x - y = 1. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 1],
                                "hint": "Add the two equations first to eliminate y.",
                                "steps": [
                                    "Add the equations: (x + y) + (x - y) = 3 + 1.",
                                    "This gives 2x = 4, so x = 2.",
                                    "Substitute x = 2 into x + y = 3 to get y = 1.",
                                ],
                            }
                        ],
                    },
                    {
                        "id": "substitution_and_elimination",
                        "title": "Algebraic Methods",
                        "explanation": (
                            "Two common methods are substitution and elimination. "
                            "Substitution works well when one variable is easy to isolate, while elimination works well when coefficients can be matched."
                        ),
                        "board_work": [
                            "2x + y = 7",
                            "x + y = 5",
                            "Subtract the second equation from the first to get x = 2, then y = 3.",
                        ],
                        "ncert_examples": [
                            {
                                "prompt": "Solve 2x + y = 7 and x + y = 5. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 3],
                                "method": "Use elimination",
                                "hint": "Subtract the second equation from the first.",
                                "steps": [
                                    "Subtract x + y = 5 from 2x + y = 7.",
                                    "This gives x = 2.",
                                    "Substitute x = 2 into x + y = 5 to get y = 3.",
                                ],
                            },
                            {
                                "prompt": "Solve 3x - y = 5 and x + y = 3. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 1],
                                "method": "Use elimination by adding the two equations",
                                "hint": "Add the equations to eliminate y.",
                                "steps": [
                                    "Add 3x - y = 5 and x + y = 3.",
                                    "This gives 4x = 8, so x = 2.",
                                    "Substitute x = 2 into x + y = 3 to get y = 1.",
                                ],
                            },
                        ],
                        "exercise_problems": [
                            {
                                "prompt": "Solve x + 2y = 7 and x - y = 1. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [3, 2],
                                "method": "Use elimination",
                                "hint": "Subtract the second equation from the first.",
                                "steps": [
                                    "Subtract x - y = 1 from x + 2y = 7.",
                                    "This gives 3y = 6, so y = 2.",
                                    "Substitute y = 2 into x - y = 1 to get x = 3.",
                                ],
                            },
                            {
                                "prompt": "Solve 3x + y = 11 and x + y = 7. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 5],
                                "method": "Use elimination",
                                "hint": "Subtract the second equation from the first.",
                                "steps": [
                                    "Subtract x + y = 7 from 3x + y = 11.",
                                    "This gives 2x = 4, so x = 2.",
                                    "Substitute x = 2 into x + y = 7 to get y = 5.",
                                ],
                            },
                        ],
                        "homework": [
                            "Solve 4x + y = 11 and 2x + y = 7.",
                            "Solve 3x + 2y = 16 and x + y = 6.",
                        ],
                        "practice_problems": [
                            {
                                "prompt": "Solve 2x + y = 7 and x + y = 5. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 3],
                                "hint": "Subtract the second equation from the first.",
                                "steps": [
                                    "Subtract x + y = 5 from 2x + y = 7.",
                                    "This gives x = 2.",
                                    "Substitute x = 2 into x + y = 5 to get y = 3.",
                                ],
                            },
                            {
                                "prompt": "Solve 3x - y = 5 and x + y = 3. Give your answer as x = ?, y = ?.",
                                "answer_type": "pair",
                                "answer": [2, 1],
                                "hint": "Add the equations to eliminate y.",
                                "steps": [
                                    "Add 3x - y = 5 and x + y = 3.",
                                    "This gives 4x = 8, so x = 2.",
                                    "Substitute x = 2 into x + y = 3 to get y = 1.",
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "slug": "quadratic_equations",
                "title": "Quadratic Equations",
                "summary": "Solving equations of degree 2 by factorisation and formula.",
                "aliases": ["quadratic equations"],
                "book_topics": [
                    "Standard Form of a Quadratic Equation",
                    "Factorisation Method",
                    "Completing the Square",
                    "Quadratic Formula",
                ],
                "homework": [
                    "Solve x^2 - 5x + 6 = 0 by factorisation.",
                    "Solve x^2 - 9 = 0.",
                    "Write the quadratic formula and identify a, b, and c in 2x^2 + 3x - 5 = 0.",
                ],
            },
            {
                "slug": "arithmetic_progressions",
                "title": "Arithmetic Progressions",
                "summary": "nth term, sum of terms, and patterns in sequences.",
                "aliases": ["arithmetic progression", "ap"],
                "book_topics": [
                    "Identifying an Arithmetic Progression",
                    "nth Term of an AP",
                    "Sum of First n Terms",
                ],
                "homework": [
                    "Find the 10th term of the AP 3, 7, 11, ...",
                    "Find the sum of the first 12 natural numbers.",
                    "Check whether 4, 9, 14, 19, ... is an AP and write its common difference.",
                ],
            },
            {
                "slug": "triangles",
                "title": "Triangles",
                "summary": "Similarity criteria and proportionality in triangles.",
                "aliases": ["triangles"],
                "book_topics": [
                    "Basic Proportionality Theorem",
                    "Criteria for Similarity of Triangles",
                    "Areas of Similar Triangles",
                    "Pythagoras Theorem and Converse",
                ],
                "homework": [
                    "State the AA similarity criterion.",
                    "In a right triangle with legs 6 cm and 8 cm, find the hypotenuse.",
                    "Write one application of the Basic Proportionality Theorem.",
                ],
            },
            {
                "slug": "coordinate_geometry",
                "title": "Coordinate Geometry",
                "summary": "Distance formula and section ideas on the Cartesian plane.",
                "aliases": ["coordinate geometry", "coordinates"],
                "book_topics": [
                    "Distance Formula",
                    "Section Formula",
                ],
                "homework": [
                    "Find the distance between (1, 2) and (4, 6).",
                    "Find the midpoint of the line segment joining (2, 3) and (8, 7).",
                    "Plot two points and check the distance formula on graph paper.",
                ],
            },
            {
                "slug": "introduction_to_trigonometry",
                "title": "Introduction to Trigonometry",
                "summary": "Trigonometric ratios and identities.",
                "aliases": ["trigonometry"],
                "book_topics": [
                    "Trigonometric Ratios",
                    "Trigonometric Identities",
                    "Values of Ratios at Specific Angles",
                    "Ratios of Complementary Angles",
                ],
                "homework": [
                    "Write the values of sin 30 degrees and cos 60 degrees.",
                    "Prove sin^2 A + cos^2 A = 1.",
                    "State the relation between tan A and cot A.",
                ],
            },
            {
                "slug": "applications_of_trigonometry",
                "title": "Applications of Trigonometry",
                "summary": "Heights and distances problems.",
                "aliases": ["applications of trigonometry", "heights and distances"],
                "book_topics": [
                    "Line of Sight",
                    "Angle of Elevation",
                    "Angle of Depression",
                    "Heights and Distances",
                ],
                "homework": [
                    "Define angle of elevation.",
                    "A tower is observed at an angle of elevation of 45 degrees from a point 20 m away. Find its height.",
                    "Draw a labelled figure for an angle of depression problem.",
                ],
            },
            {
                "slug": "circles",
                "title": "Circles",
                "summary": "Tangents and their properties.",
                "aliases": ["circles"],
                "book_topics": [
                    "Tangent to a Circle",
                    "Number of Tangents from a Point",
                    "Lengths of Tangents from an External Point",
                ],
                "homework": [
                    "State the theorem about tangents from an external point.",
                    "How many tangents can be drawn from a point outside a circle?",
                    "Draw a circle and a tangent at a point of contact.",
                ],
            },
            {
                "slug": "constructions",
                "title": "Constructions",
                "summary": "Dividing line segments and constructing tangents.",
                "aliases": ["constructions"],
                "book_topics": [
                    "Division of a Line Segment",
                    "Construction of Similar Triangles",
                    "Construction of Tangents to a Circle",
                ],
                "homework": [
                    "Write the steps to divide a line segment in the ratio 3:2.",
                    "State the key idea used in constructing a tangent from an external point.",
                    "Practise one neat labelled construction from the chapter.",
                ],
            },
            {
                "slug": "areas_related_to_circles",
                "title": "Areas Related to Circles",
                "summary": "Arc length, sector area, and related measurements.",
                "aliases": ["areas related to circles"],
                "book_topics": [
                    "Perimeter and Area of a Circle",
                    "Arc Length",
                    "Area of a Sector",
                    "Area of a Segment",
                ],
                "homework": [
                    "Find the area of a circle of radius 7 cm.",
                    "Find the arc length for a 90 degree sector of radius 14 cm.",
                    "Write the formula for the area of a sector.",
                ],
            },
            {
                "slug": "surface_areas_and_volumes",
                "title": "Surface Areas and Volumes",
                "summary": "Composite solids and conversions of shapes.",
                "aliases": ["surface area", "volume"],
                "book_topics": [
                    "Surface Area of Solids",
                    "Volume of Solids",
                    "Combination of Solids",
                    "Conversion of Solids",
                ],
                "homework": [
                    "Find the volume of a cylinder of radius 3 cm and height 7 cm.",
                    "Write the curved surface area formula for a cone.",
                    "Identify two examples of combination solids from daily life.",
                ],
            },
            {
                "slug": "statistics",
                "title": "Statistics",
                "summary": "Grouped data, mean, median, and mode.",
                "aliases": ["statistics"],
                "book_topics": [
                    "Mean of Grouped Data",
                    "Median of Grouped Data",
                    "Mode of Grouped Data",
                    "Cumulative Frequency Curves",
                ],
                "homework": [
                    "State the formula for the mean using the direct method.",
                    "Define median in one sentence.",
                    "Write one difference between mean and mode.",
                ],
            },
            {
                "slug": "probability",
                "title": "Probability",
                "summary": "Theoretical probability and simple experiments.",
                "aliases": ["probability"],
                "book_topics": [
                    "Theoretical Probability",
                    "Equally Likely Outcomes",
                    "Simple Events",
                    "Probability in Daily Situations",
                ],
                "homework": [
                    "Find the probability of getting a head when a coin is tossed once.",
                    "Find the probability of getting an even number on a fair die.",
                    "Explain what makes outcomes equally likely.",
                ],
            },
        ],
    },
}


def get_grade_curriculum(grade: int) -> dict:
    return GRADE_CURRICULUM.get(grade, GRADE_CURRICULUM[10])


def list_chapters(grade: int) -> list[dict]:
    return get_grade_curriculum(grade)["chapters"]


def get_default_topic_slug(grade: int) -> str:
    return get_grade_curriculum(grade)["default_topic_slug"]


def get_topic(grade: int, topic_slug: str | None = None) -> dict | None:
    slug = topic_slug or get_default_topic_slug(grade)
    for chapter in list_chapters(grade):
        if chapter["slug"] == slug:
            return chapter
    return None


def get_chapter_position(grade: int, topic_slug: str | None) -> tuple[int, int]:
    chapters = list_chapters(grade)
    total = len(chapters)
    if not chapters:
        return (1, 1)

    slug = topic_slug or chapters[0]["slug"]
    for index, chapter in enumerate(chapters, start=1):
        if chapter["slug"] == slug:
            return (index, total)
    return (1, total)


def _fallback_concepts(topic: dict) -> list[dict]:
    title = topic.get("title", "CBSE Mathematics")
    summary = topic.get("summary", "")
    anchor = topic.get("teaching_anchor", "")
    topic_titles = [item.strip() for item in topic.get("book_topics", []) if item and item.strip()]
    if not topic_titles:
        topic_titles = [title]

    concepts: list[dict] = []
    for index, book_topic in enumerate(topic_titles, start=1):
        board_work = []
        if index == 1 and anchor:
            board_work.append(anchor)
        board_work.append(f"Topic focus: {book_topic}")
        if summary:
            board_work.append(summary)

        explanation_parts = [
            f"In this part of {title}, we study {book_topic.lower()}.",
        ]
        if summary:
            explanation_parts.append(summary)

        concepts.append(
            {
                "id": f"{topic['slug']}_topic_{index}",
                "title": book_topic,
                "explanation": " ".join(part for part in explanation_parts if part).strip(),
                "board_work": board_work[:3],
                "practice_problems": [],
            }
        )
    return concepts


def get_topic_concepts(grade: int, topic_slug: str) -> list[dict]:
    topic = get_topic(grade, topic_slug)
    if not topic:
        return []

    concepts = topic.get("concepts", [])
    if concepts:
        return concepts

    return _fallback_concepts(topic)


def get_concept(grade: int, topic_slug: str, concept_id: str | None = None) -> dict | None:
    concepts = get_topic_concepts(grade, topic_slug)
    if not concepts:
        return None

    if concept_id is None:
        return concepts[0]

    for concept in concepts:
        if concept["id"] == concept_id:
            return concept
    return None


def get_next_concept(grade: int, topic_slug: str, current_concept_id: str | None) -> dict | None:
    concepts = get_topic_concepts(grade, topic_slug)
    if not concepts:
        return None

    if current_concept_id is None:
        return concepts[0]

    for index, concept in enumerate(concepts):
        if concept["id"] == current_concept_id and index + 1 < len(concepts):
            return concepts[index + 1]
    return None


def get_next_topic(grade: int, current_topic_slug: str | None) -> dict | None:
    chapters = list_chapters(grade)
    if not chapters:
        return None

    if current_topic_slug is None:
        return chapters[0]

    for index, chapter in enumerate(chapters):
        if chapter["slug"] == current_topic_slug:
            if index + 1 < len(chapters):
                return chapters[index + 1]
            return None
    return chapters[0]


def find_topic_by_message(grade: int, message: str) -> dict | None:
    lower = message.lower()
    for chapter in list_chapters(grade):
        search_terms = [chapter["title"].lower(), chapter["slug"].replace("_", " ")]
        search_terms.extend(alias.lower() for alias in chapter.get("aliases", []))
        if any(term in lower for term in search_terms):
            return chapter
    return None


def build_curriculum_grounding(grade: int) -> str:
    curriculum = get_grade_curriculum(grade)
    chapter_titles = ", ".join(chapter["title"] for chapter in curriculum["chapters"])
    return (
        f"Board: {curriculum['board']}\n"
        f"Subject: {curriculum['subject']}\n"
        f"Grade: {grade}\n"
        f"Chapters: {chapter_titles}"
    )
