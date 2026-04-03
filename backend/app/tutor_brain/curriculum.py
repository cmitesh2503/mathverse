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
        "default_topic_slug": "pair_of_linear_equations_in_two_variables",
        "chapters": [
            {
                "slug": "real_numbers",
                "title": "Real Numbers",
                "summary": "Euclid's division lemma, HCF, and irrational numbers.",
                "aliases": ["real numbers"],
            },
            {
                "slug": "polynomials",
                "title": "Polynomials",
                "summary": "Zeros of polynomials and relations with coefficients.",
                "aliases": ["polynomials"],
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
                "concepts": [
                    {
                        "id": "graphical_meaning",
                        "title": "What a Pair of Equations Represents",
                        "explanation": (
                            "Each linear equation represents a straight line. "
                            "The common solution of two equations is the point where the two lines intersect."
                        ),
                        "board_work": [
                            "x + y = 3 and x - y = 1",
                            "The solution is the point that satisfies both equations at once.",
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
            },
            {
                "slug": "arithmetic_progressions",
                "title": "Arithmetic Progressions",
                "summary": "nth term, sum of terms, and patterns in sequences.",
                "aliases": ["arithmetic progression", "ap"],
            },
            {
                "slug": "triangles",
                "title": "Triangles",
                "summary": "Similarity criteria and proportionality in triangles.",
                "aliases": ["triangles"],
            },
            {
                "slug": "coordinate_geometry",
                "title": "Coordinate Geometry",
                "summary": "Distance formula and section ideas on the Cartesian plane.",
                "aliases": ["coordinate geometry", "coordinates"],
            },
            {
                "slug": "introduction_to_trigonometry",
                "title": "Introduction to Trigonometry",
                "summary": "Trigonometric ratios and identities.",
                "aliases": ["trigonometry"],
            },
            {
                "slug": "applications_of_trigonometry",
                "title": "Applications of Trigonometry",
                "summary": "Heights and distances problems.",
                "aliases": ["applications of trigonometry", "heights and distances"],
            },
            {
                "slug": "circles",
                "title": "Circles",
                "summary": "Tangents and their properties.",
                "aliases": ["circles"],
            },
            {
                "slug": "constructions",
                "title": "Constructions",
                "summary": "Dividing line segments and constructing tangents.",
                "aliases": ["constructions"],
            },
            {
                "slug": "areas_related_to_circles",
                "title": "Areas Related to Circles",
                "summary": "Arc length, sector area, and related measurements.",
                "aliases": ["areas related to circles"],
            },
            {
                "slug": "surface_areas_and_volumes",
                "title": "Surface Areas and Volumes",
                "summary": "Composite solids and conversions of shapes.",
                "aliases": ["surface area", "volume"],
            },
            {
                "slug": "statistics",
                "title": "Statistics",
                "summary": "Grouped data, mean, median, and mode.",
                "aliases": ["statistics"],
            },
            {
                "slug": "probability",
                "title": "Probability",
                "summary": "Theoretical probability and simple experiments.",
                "aliases": ["probability"],
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


def get_concept(grade: int, topic_slug: str, concept_id: str | None = None) -> dict | None:
    topic = get_topic(grade, topic_slug)
    if not topic:
        return None

    concepts = topic.get("concepts", [])
    if not concepts:
        return None

    if concept_id is None:
        return concepts[0]

    for concept in concepts:
        if concept["id"] == concept_id:
            return concept
    return None


def get_next_concept(grade: int, topic_slug: str, current_concept_id: str | None) -> dict | None:
    topic = get_topic(grade, topic_slug)
    if not topic:
        return None

    concepts = topic.get("concepts", [])
    if not concepts:
        return None

    if current_concept_id is None:
        return concepts[0]

    for index, concept in enumerate(concepts):
        if concept["id"] == current_concept_id and index + 1 < len(concepts):
            return concepts[index + 1]
    return None


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
