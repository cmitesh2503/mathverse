# Curriculum structure: Topics → Concepts → Questions

CURRICULUM = {
    "linear_equations": {
        "topic_name": "Linear Equations",
        "grade": 10,
        "concepts": [
            {
                "id": "simple_equations",
                "name": "Simple Equations (x + a = b)",
                "description": "Learn to solve basic equations",
                "example_problem": "x + 5 = 12",
                "steps": [
                    "Subtract 5 from both sides",
                    "x = 7"
                ],
                "practice_problems": [
                    {"equation": "x + 3 = 8", "answer": 5},
                    {"equation": "x + 10 = 25", "answer": 15},
                    {"equation": "x + 7 = 20", "answer": 13},
                ]
            },
            {
                "id": "two_step_equations",
                "name": "Two-Step Equations (ax + b = c)",
                "description": "Solve equations with multiplication/division",
                "example_problem": "2x + 3 = 7",
                "steps": [
                    "Subtract 3 from both sides → 2x = 4",
                    "Divide by 2 → x = 2"
                ],
                "practice_problems": [
                    {"equation": "2x + 5 = 13", "answer": 4},
                    {"equation": "3x + 2 = 11", "answer": 3},
                    {"equation": "4x + 1 = 17", "answer": 4},
                ]
            },
            {
                "id": "multi_step_equations",
                "name": "Multi-Step Equations (ax - b = c)",
                "description": "Solve more complex equations",
                "example_problem": "3x - 6 = 18",
                "steps": [
                    "Add 6 to both sides → 3x = 24",
                    "Divide by 3 → x = 8"
                ],
                "practice_problems": [
                    {"equation": "5x - 10 = 40", "answer": 10},
                    {"equation": "2x - 3 = 7", "answer": 5},
                    {"equation": "4x - 8 = 12", "answer": 5},
                ]
            },
            {
                "id": "var_both_sides",
                "name": "Variables on Both Sides",
                "description": "Equations with x on both sides",
                "example_problem": "2x + 3 = x + 7",
                "steps": [
                    "Subtract x from both sides → x + 3 = 7",
                    "Subtract 3 from both sides → x = 4"
                ],
                "practice_problems": [
                    {"equation": "3x = x + 8", "answer": 4},
                    {"equation": "2x + 1 = x + 5", "answer": 4},
                    {"equation": "5x = 2x + 9", "answer": 3},
                ]
            }
        ]
    }
}

def get_topic(topic_name: str):
    return CURRICULUM.get(topic_name)

def get_concept(topic_name: str, concept_id: str):
    topic = CURRICULUM.get(topic_name)
    if topic:
        for concept in topic["concepts"]:
            if concept["id"] == concept_id:
                return concept
    return None

def get_next_concept(topic_name: str, current_concept_id: str):
    topic = CURRICULUM.get(topic_name)
    if topic:
        for i, concept in enumerate(topic["concepts"]):
            if concept["id"] == current_concept_id:
                if i + 1 < len(topic["concepts"]):
                    return topic["concepts"][i + 1]
    return None
