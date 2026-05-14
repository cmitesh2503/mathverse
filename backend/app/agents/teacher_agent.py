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
    SYSTEM_PROMPT = """You are Arvind Sir, a highly professional, expert Mathematics tutor for Grade {grade} {exam} students.

AVAILABLE KNOWLEDGE (RAG CONTEXT):
{rag_context}
You MUST base your syllabus, weightage, and problems strictly on the information provided above.

TEACHING FLOW DIRECTIVES:

IF THIS IS A NEW CHAPTER (is_new_chapter is True):
Enthusiastically welcome the student to Grade {grade} {exam} Math.

Introduce the Chapter.

Exam Strategy: Tell the student the historical weightage of this chapter in the {exam} exam and what kind of questions usually appear based on PYQs.

WHITEBOARD: Use whiteboard_actions to write the Chapter Name and the Agenda/List of topics on the board.

IF THIS IS A CONTINUING CLASS (is_new_chapter is False, but is_first_interaction is True):
Welcome the student back.

Give a very brief 1-2 sentence recap of what was covered in the last class.

State the topic for today and use whiteboard_actions to write it on the board.

THE PEDAGOGICAL LOOP (HOW YOU TEACH - GUIDED EXPLAINER):
When teaching a topic or solving a problem, follow this approach:

Clear Explanation: Explain the core concept or the problem-solving strategy clearly and simply. Do NOT force the student to guess the strategy.

Step-by-Step Whiteboard: Write the problem on the board and solve it step-by-step.

Strategic Questioning (Don't Overdo It): Do NOT ask a question for every single step. Explain 2-3 steps yourself. Then, occasionally ask a checking question like, "Are you with me so far?" or "If we apply that formula here, what do you think the next term will be?"

The "Move On" Rule (CRITICAL): If the student gives a wrong answer, says "I don't know", is silent, or seems confused, DO NOT badger them or get stuck in a loop. Say something encouraging like, "That's okay, this is a tricky part," then IMMEDIATELY explain the correct logic, write the next step on the board, and continue the lesson flow smoothly. Do not wait for them to guess again.

MANDATORY CLASS SYNC RULES:
Every response must keep voice explanation and whiteboard content in sync.
Always include current chapter and topic on the board:
1) "Chapter: <chapter_name>"
2) "Topic: <current_topic>"
For each topic, teach in this strict order:
1) Concept explanation first
2) One solved PYQ-style problem
3) One solved study-material problem
4) One generated similar problem based on PYQ pattern
All problem explanations must be step-by-step on the board.
"""

    async def process_message(
        self,
        session: StudentSession,
        user_message: str,
        diagnostic_nudge: str = None,
        rag_context: str = "",
    ) -> dict:
        was_first_interaction = session.is_first_interaction
        prompt = self._build_prompt(session, user_message, diagnostic_nudge, rag_context=rag_context)
        raw_response = await asyncio.to_thread(generate_response, prompt)
        result = self._parse_agent_response(raw_response)

        if not result["whiteboard_actions"]:
            if was_first_interaction:
                result["whiteboard_actions"] = self._opening_whiteboard_actions(session)
            else:
                result["whiteboard_actions"] = self._fallback_whiteboard_actions(result["spoken_response"])

        if session.is_first_interaction:
            session.is_first_interaction = False

        session.next_system_note = None
        return result

    def _build_prompt(
        self,
        session: StudentSession,
        user_message: str,
        diagnostic_nudge: str | None,
        rag_context: str,
    ) -> str:
        current_problem = json.dumps(session.current_problem or {}, ensure_ascii=False)
        mistake_history = json.dumps(session.mistake_history or [], ensure_ascii=False)
        agenda = json.dumps(session.agenda or [], ensure_ascii=False)
        
        # Determine if this is a new chapter
        is_new_chapter = session.is_first_interaction
        
        # Resolve system prompt with dynamic variables
        resolved_system_prompt = self.SYSTEM_PROMPT.format(
            grade=session.grade,
            exam=session.exam.upper(),
            is_new_chapter=is_new_chapter,
            rag_context=rag_context or "No RAG context provided.",
        )

        system_notes: list[str] = []
        if session.is_first_interaction:
            system_notes.append(
                f"CRITICAL DIRECTIVE: This is the FIRST interaction - Class is NOW STARTING. "
                f"DO NOT wait for student input. "
                f"IMMEDIATELY follow the 'IF THIS IS A NEW CHAPTER' flow:\n"
                f"1. Enthusiastically welcome the student to Grade {session.grade} {session.exam.upper()} Math\n"
                f"2. Introduce the Chapter: {session.chapter_name}\n"
                f"3. Provide exam strategy and historical weightage for {session.exam.upper()}\n"
                f"4. Use whiteboard_actions to write Chapter Name and full Agenda on board\n"
                f"5. Begin with a clear explanation of the first topic\n"
                f"Agenda items: {agenda}\n"
                f"Do not ask questions yet - TEACH FIRST, ASK LATER.\n"
                f"After concept explanation, show problem flow in order: PYQ -> Study Material -> Generated Similar."
            )
        else:
            system_notes.append(
                "CRITICAL CONTINUITY DIRECTIVE: This is an ongoing turn in the SAME class session. "
                "Do NOT greet again. Do NOT recap previous class/session unless explicitly asked by the student. "
                "Continue teaching from the current topic and board state immediately. "
                "Keep momentum and write concrete, meaningful whiteboard content. "
                "Maintain chapter/topic headers and continue concept -> PYQ -> study-material -> generated problem flow."
            )

        if session.next_system_note:
            system_notes.append(session.next_system_note)

        system_note = "\n".join(system_notes)

        return (
            f"{system_note}\n\n"
            f"{resolved_system_prompt}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- session_id: {session.session_id}\n"
            f"- grade: {session.grade}\n"
            f"- exam: {session.exam}\n"
            f"- is_new_chapter: {is_new_chapter}\n"
            f"- chapter_name: {session.chapter_name}\n"
            f"- agenda: {agenda}\n"
            f"- current_topic_index: {session.current_topic_index}\n"
            f"- current_topic: {session.current_topic or 'unknown'}\n"
            f"- difficulty_level: {session.difficulty_level}\n"
            f"- active_phase: {getattr(session.active_phase, 'value', session.active_phase)}\n"
            f"- mistake_history: {mistake_history}\n"
            f"- current_problem: {current_problem}\n\n"
            f"STUDENT MESSAGE:\n{user_message}\n\n"
            f"HIDDEN DIAGNOSTIC NUDGE:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only.\n"
            "No markdown fences. No prose outside JSON.\n"
            "Top-level keys must be EXACTLY:\n"
            '1) "spoken_response": string\n'
            '2) "whiteboard_actions": array of action objects\n'
            "When introducing chapter/agenda or solving a problem, include meaningful whiteboard_actions.\n"
            "Follow the PEDAGOGICAL LOOP: Clear Explanation -> Step-by-Step Whiteboard -> Strategic Questioning -> Move On Rule."
        )

    def _opening_whiteboard_actions(self, session: StudentSession) -> list[dict[str, Any]]:
        agenda_lines = [f"{index + 1}. {topic}" for index, topic in enumerate(session.agenda or [])]
        agenda_text = "Agenda:\n" + ("\n".join(agenda_lines) if agenda_lines else "1. Topic overview")
        exam_label = session.exam.upper() if hasattr(session, 'exam') else "CBSE"
        return [
            {"action": "draw_text", "content": f"Grade {session.grade} {exam_label} Mathematics"},
            {"action": "draw_text", "content": f"Chapter: {session.chapter_name}"},
            {"action": "draw_text", "content": agenda_text},
        ]

    def _parse_agent_response(self, raw_response: str) -> dict:
        payload = self._load_json_object(raw_response)
        spoken_response = payload.get("spoken_response")
        whiteboard_actions = payload.get("whiteboard_actions")

        # Some model responses contain nested JSON encoded as a string.
        if isinstance(spoken_response, str):
            nested = self._load_json_object(spoken_response)
            if nested:
                nested_spoken = nested.get("spoken_response")
                nested_actions = nested.get("whiteboard_actions")
                if isinstance(nested_spoken, str):
                    spoken_response = nested_spoken
                if not isinstance(whiteboard_actions, list) and isinstance(nested_actions, list):
                    whiteboard_actions = nested_actions

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

        parsed = self._try_parse_json_dict(text)
        if parsed:
            return parsed

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            parsed = self._try_parse_json_dict(match.group(0))
            if parsed:
                return parsed

        return self._extract_loose_fields(text)

    def _try_parse_json_dict(self, text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                return {}

        return parsed if isinstance(parsed, dict) else {}

    def _extract_loose_fields(self, text: str) -> dict[str, Any]:
        if "\"spoken_response\"" not in text:
            return {}

        spoken_response = ""
        whiteboard_actions: list[Any] = []

        spoken_match = re.search(r'"spoken_response"\s*:\s*', text)
        if spoken_match:
            spoken_start = spoken_match.end()
            whiteboard_key_index = text.find('"whiteboard_actions"', spoken_start)
            spoken_chunk = text[spoken_start:whiteboard_key_index] if whiteboard_key_index != -1 else text[spoken_start:]
            spoken_chunk = spoken_chunk.strip().rstrip(",")

            if spoken_chunk.startswith('"'):
                try:
                    spoken_response = json.loads(spoken_chunk)
                except json.JSONDecodeError:
                    spoken_response = spoken_chunk.strip('"')
            else:
                spoken_response = spoken_chunk

            spoken_response = spoken_response.replace('\\"', '"').strip()

        whiteboard_key_index = text.find('"whiteboard_actions"')
        if whiteboard_key_index != -1:
            array_start = text.find("[", whiteboard_key_index)
            if array_start != -1:
                array_end = self._find_matching_bracket(text, array_start)
                if array_end != -1:
                    array_text = text[array_start:array_end + 1]
                    try:
                        parsed_actions = json.loads(array_text)
                        if isinstance(parsed_actions, list):
                            whiteboard_actions = parsed_actions
                    except json.JSONDecodeError:
                        whiteboard_actions = []

        result: dict[str, Any] = {}
        if spoken_response:
            result["spoken_response"] = spoken_response
        if whiteboard_actions:
            result["whiteboard_actions"] = whiteboard_actions
        return result

    def _find_matching_bracket(self, text: str, start_index: int) -> int:
        depth = 0
        in_string = False
        escaped = False

        for index in range(start_index, len(text)):
            char = text[index]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return index

        return -1

    def _sanitize_whiteboard_actions(self, actions: list[Any]) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue

            action_name = action.get("action")
            if not isinstance(action_name, str) or not action_name.strip():
                continue

            action_name = action_name.strip()
            clean_action: dict[str, Any] = {"action": action_name}

            content_value = (
                action.get("content")
                or action.get("text")
                or action.get("value")
                or action.get("message")
                or action.get("expression")
                or action.get("label")
            )

            if isinstance(content_value, str) and content_value.strip():
                clean_action["content"] = content_value.strip()

            for key in ("label", "expression", "points", "metadata"):
                if key in action and key not in clean_action:
                    clean_action[key] = action[key]

            if action_name.lower() in {"clear", "clear_board", "erase", "reset_board"} and "content" not in clean_action:
                # Allow structural board reset actions, but they won't be used as step text.
                sanitized.append(clean_action)
                continue

            if "content" not in clean_action and action_name.lower() in {"write", "write_text", "add_text", "text"}:
                # Generic write actions without payload add no value to the smart board.
                continue

            sanitized.append(clean_action)

        return sanitized

    def _fallback_whiteboard_actions(self, spoken_response: str) -> list[dict[str, Any]]:
        if not isinstance(spoken_response, str) or not spoken_response.strip():
            return []

        lines = [line.strip() for line in re.split(r"[\n\.]+", spoken_response) if line.strip()]
        snippets = lines[:3] if lines else [spoken_response.strip()]
        return [{"action": "draw_text", "content": snippet} for snippet in snippets]


def decide_mode(message: str, state: str) -> str:
    message = message.lower()

    if message.strip() in ["hi", "hello", "hey"]:
        return "GREETING"

    if any(word in message for word in ["pause", "stop", "break"]):
        return "BREAK"

    if any(word in message for word in ["don't understand", "doubt", "why", "what"]):
        return "DOUBT"

    return "LEARNING"

