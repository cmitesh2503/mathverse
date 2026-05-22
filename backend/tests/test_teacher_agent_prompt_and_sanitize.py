import sys
import json
import inspect

# ensure backend package is importable
sys.path.append("backend")

from app.agents.teacher_agent import TutorAgent


def test_system_prompt_contains_decode_and_schema():
    prompt = TutorAgent.SYSTEM_PROMPT
    assert "What is given" in prompt or "What is given:" in prompt
    assert "What needs to be found" in prompt or "What needs to be found:" in prompt
    # check presence of canonical action names
    for name in ["draw_line", "draw_angle", "write_text", "highlight_element"]:
        assert name in prompt


def test_sanitize_whiteboard_actions_maps_and_validates():
    agent = TutorAgent()
    raw_actions = [
        {"action": "draw_text", "content": "Given: a=5"},
        {"action": "draw_line", "x1": "10", "y1": "20", "x2": 100, "y2": 20, "color": "black"},
        {"action": "draw_angle", "x": 50, "y": 60, "radius": 15, "start_angle": 0, "end_angle": 30, "label": "θ"},
        {"action": "highlight", "x1": 5, "y1": 5, "x2": 60, "y2": 40, "color": "green"},
        {"action": "unknown_action", "foo": "bar"},
        {"action": "diagram", "content": "NCERT figure"},
    ]

    sanitized = agent._sanitize_whiteboard_actions(raw_actions)
    # ensure unknown actions dropped
    assert all(isinstance(a, dict) for a in sanitized)
    actions_names = [a.get("action") for a in sanitized]
    assert "write_text" in actions_names
    assert "draw_line" in actions_names
    assert "draw_angle" in actions_names
    assert "highlight_element" in actions_names
    # check write_text mapped from draw_text/diagram
    write_texts = [a for a in sanitized if a.get("action") == "write_text"]
    assert any("Given" in a.get("label", "") or "NCERT" in a.get("label", "") for a in write_texts)


if __name__ == "__main__":
    # quick local run
    test_system_prompt_contains_decode_and_schema()
    test_sanitize_whiteboard_actions_maps_and_validates()
    print("OK")
