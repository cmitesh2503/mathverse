import json
import pytest

from backend.app.services import geometry_translator as gt


def test_translate_with_mocked_model(monkeypatch):
    # Mock generate_response to return a valid JSON
    def fake_generate(prompt, model=None):
        return json.dumps({
            "whiteboard_actions": [
                {"action": "write_text", "x": 10, "y": 10, "label": "What is given: a=5"}
            ]
        })

    monkeypatch.setattr(gt, "generate_response", fake_generate)
    actions = gt.translate_diagram_to_primitives("triangle with vertices", model="test")
    assert isinstance(actions, list)
    assert any(a.get("action") in {"write_text", "draw_line"} for a in actions)


def test_translate_fallback_on_invalid_model_output(monkeypatch):
    # Mock generate_response to return invalid text
    def fake_generate(prompt, model=None):
        return "I cannot produce JSON"

    monkeypatch.setattr(gt, "generate_response", fake_generate)
    actions = gt.translate_diagram_to_primitives("triangle with vertices", model="test")
    # Heuristic fallback should at least produce draw_line elements for triangle
    assert isinstance(actions, list)
    assert any(a.get("action") == "draw_line" for a in actions)
