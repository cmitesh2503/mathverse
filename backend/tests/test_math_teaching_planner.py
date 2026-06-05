import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.math_teaching_planner import _json_object


def test_json_object_repairs_missing_comma_between_fields():
    raw = """
```json
{
  "problem_type": "circle_tangent"
  "given": ["circle with centre O"],
  "to_find": "parallel tangents",
  "diagram": {"objects": [{"type": "circle", "center": "O"}]},
  "solution_steps": ["Use tangent-radius theorem."],
  "answer": "Tangents are parallel.",
}
```
"""

    parsed = _json_object(raw)

    assert parsed["problem_type"] == "circle_tangent"
    assert parsed["given"] == ["circle with centre O"]
    assert parsed["diagram"]["objects"][0]["type"] == "circle"


def test_json_object_returns_empty_dict_for_unrepairable_json():
    assert _json_object('Model output: {"problem_type": "circle", "given": [}') == {}
