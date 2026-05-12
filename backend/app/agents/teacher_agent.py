from __future__ import annotations

import asyncio
import json
import re
from typing import Any

try:
    from app.models.session import StudentSession
    from app.services.ai_gateway import generate_response
except ModuleNotFoundError:
    from ..models.session import StudentSession
    from ..services.ai_gateway import generate_response


class TutorAgent:
    SYSTEM_PROMPT = """You are Arvind Sir, a highly energetic, polite, professional, and motivating Mathematics teacher coaching students for CBSE and the IIT-JEE exam.

YOUR PERSONALITY & VOICE:

You are live, dynamic, and deeply passionate about math.

You act as a mentor. Frequently weave in quick, high-value advice on how to prepare, avoid negative marking, and achieve top percentiles in JEE/CBSE.

Speak naturally. Use ellipses (...) for slight pauses.

YOUR TEACHING PACING & PROTOCOL (CRITICAL):

Balanced Explanation: Explain concepts clearly using your whiteboard. You do NOT need to end every single sentence with a question. It is okay to explain a full concept block.

Strategic Questions: Ask checking questions occasionally, but do not overdo it.

The 'Move On' Rule: If the student is silent, says "I don't know," gives a wrong answer, or seems stuck, DO NOT badger them. Gracefully provide the exact correct answer, explain the logic simply, and immediately continue the flow of the class.

Encouragement: If a student misses something, motivate them (e.g., "No worries, this is a classic JEE trap, now you know it! Let's move to the next step...").

YOUR WHITEBOARD CONTROL:

Whenever a problem involves geometry, graphs, or complex equations, you MUST trigger a whiteboard action to draw it alongside your explanation.
"""

    async def process_message(
        self,
        session: StudentSession,
        user_message: str,
        diagnostic_nudge: str = None,
    ) -> dict:
        prompt = self._build_prompt(session, user_message, diagnostic_nudge)
        raw_response = await asyncio.to_thread(generate_response, prompt)
        result = self._parse_agent_response(raw_response)
        
        # After the first interaction, mark it as complete
        if session.is_first_interaction:
            session.is_first_interaction = False
        
        return result

    def _build_prompt(
        self,
        session: StudentSession,
        user_message: str,
        diagnostic_nudge: str | None,
    ) -> str:
        current_problem = json.dumps(session.current_problem or {}, ensure_ascii=False)
        mistake_history = json.dumps(session.mistake_history or [], ensure_ascii=False)
        agenda = json.dumps(session.agenda or [], ensure_ascii=False)

        system_note = ""
        if session.is_first_interaction:
            system_note = (
                f"SYSTEM NOTE: This is the beginning of the class. "
                f"The chapter is {session.chapter_name}. "
                f"The agenda is {agenda}. "
                f"Greet the student warmly, announce the chapter, display the agenda on the whiteboard, "
                f"and transition into an engaging first question.\n\n"
            )

        return (
            f"{system_note}"
            f"{self.SYSTEM_PROMPT}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- session_id: {session.session_id}\n"
            f"- current_topic: {session.current_topic or 'unknown'}\n"
            f"- difficulty_level: {session.difficulty_level}\n"
            f"- active_phase: {getattr(session.active_phase, 'value', session.active_phase)}\n"
            f"- mistake_history: {mistake_history}\n"
            f"- current_problem: {current_problem}\n\n"
            f"STUDENT MESSAGE:\n{user_message}\n\n"
            f"HIDDEN DIAGNOSTIC NUDGE:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only. Do not wrap it in markdown. Do not add commentary.\n"
            "The JSON object must contain EXACTLY these two keys:\n"
            '1. "spoken_response": a natural response in Arvind Sir voice, balancing explanation and engagement.\n'
            '2. "whiteboard_actions": an array of objects. Use objects such as '
            '{"action":"draw_text","content":"..."} or {"action":"write_equation","content":"..."} '
            'or {"action":"draw_circle"} when a visual is needed.\n'
            "No other top-level keys are allowed."
        )

    def _parse_agent_response(self, raw_response: str) -> dict:
        payload = self._load_json_object(raw_response)
        spoken_response = payload.get("spoken_response")
        whiteboard_actions = payload.get("whiteboard_actions")

        if not isinstance(spoken_response, str):
            spoken_response = raw_response.strip()

        if not isinstance(whiteboard_actions, list):
            whiteboard_actions = []

        return {
            "spoken_response": spoken_response,
            "whiteboard_actions": self._sanitize_whiteboard_actions(whiteboard_actions),
        }

    def _load_json_object(self, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return {}
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

        return parsed if isinstance(parsed, dict) else {}

    def _sanitize_whiteboard_actions(self, actions: list[Any]) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue

            action_name = action.get("action")
            if not isinstance(action_name, str) or not action_name.strip():
                continue

            clean_action: dict[str, Any] = {"action": action_name.strip()}
            for key in ("content", "label", "expression", "points", "metadata"):
                if key in action:
                    clean_action[key] = action[key]
            sanitized.append(clean_action)

        return sanitized


def decide_mode(message: str, state: str) -> str:
    message = message.lower()

    if message.strip() in ["hi", "hello", "hey"]:
        return "GREETING"

    if any(word in message for word in ["pause", "stop", "break"]):
        return "BREAK"

    if any(word in message for word in ["don't understand", "doubt", "why", "what"]):
        return "DOUBT"

    return "LEARNING"
