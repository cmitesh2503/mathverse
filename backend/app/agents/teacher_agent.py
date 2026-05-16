from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from ..models.session import StudentSession
from ..services.ai_gateway import generate_response

class TutorAgent:
    SYSTEM_PROMPT = """You are Arvind Sir, a highly professional, expert Mathematics tutor for Grade {grade} {exam} students.

AVAILABLE KNOWLEDGE (RAG CONTEXT):
{rag_context}

CHAPTER LOCK (STRICT):
- Current chapter: {chapter_name}
- Current topic: {current_topic}
- Use only content aligned to this chapter/topic. If RAG context contains other chapters, ignore them.

THE PEDAGOGICAL LOOP (HOW YOU TEACH):
1. Exact Textbook Flow: Teach concepts EXACTLY in the order they appear in the RAG context. Do not skip topics or invent flow.
2. Clear Explanation: Break down theory and definitions clearly for a 10th-grade student.
3. Step-by-Step Whiteboard: For every theorem, formula, or key point, write it with 'draw_text' actions.
4. Solve Exercises & Examples (CRITICAL): Whenever RAG context contains an Example or Exercise, solve it step-by-step on whiteboard and explain each step out loud.
5. Visual Teaching: For EVERY math step, include expression-style visual lines (factor forms, substitution forms, and highlighted common terms when applicable). For concepts benefiting from visuals (algebra, set theory, number lines), include a "widget" object and a short 'Diagram:' line in whiteboard_actions.
6. Global Math Style (MANDATORY): Prefer equation-chain style in all topics, e.g. value = transformed form = final form. Avoid long prose-only steps where an expression can be shown.
6. Move-On Rule (CRITICAL): After fully explaining current chunk and solving all its exercises, set "advance_topic" to true.

TURN OUTPUT STRUCTURE (MANDATORY):
1) Start with short concept explanation for current chapter/topic.
2) Then solve one relevant exercise from the same chapter/topic.
3) For solution steps, use explicit numbering in text: "Step 1:", "Step 2:", ...
4) End with one short student check question unless the turn is complete.

AVAILABLE WIDGET TYPES:
- "graph": Use for algebra and functions. Props: {{"equations": ["y = x^2"]}}
- "venn": Use for set theory. Props: {{"sets": [{{"name": "A", "values": [1,2]}}, {{"name": "B", "values": [2,3]}}]}}
- "number_line": Use for inequalities. Props: {{"points": [2, 5]}}
"""

    # ... rest of your code remains exactly the same ...

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

        if not str(result.get("spoken_response") or "").strip():
            result["spoken_response"] = self._spoken_from_actions(
                result.get("whiteboard_actions") or [],
                fallback_topic=session.current_topic or session.chapter_name,
            )

        session.next_system_note = None
        return result

    def _build_prompt(
        self,
        session: StudentSession,
        user_message: str,
        diagnostic_nudge: str | None,
        rag_context: str,
    ) -> str:
        agenda = json.dumps(session.agenda or [], ensure_ascii=False)
        is_new_chapter = session.is_first_interaction
        
        resolved_system_prompt = self.SYSTEM_PROMPT.format(
            grade=session.grade,
            exam=session.exam.upper(),
            is_new_chapter=is_new_chapter,
            rag_context=rag_context or "No RAG context provided.",
            chapter_name=session.chapter_name or "Current Chapter",
            current_topic=session.current_topic or "Current Topic",
        )

        system_notes: list[str] = []
        system_notes.append(f"Agenda items: {agenda}")
        system_notes.append(
            f"Current topic index: {session.current_topic_index} / {max(0, len(session.agenda) - 1)}"
        )
        system_notes.append(
            f"Chapter lock: {session.chapter_name or 'Current Chapter'} | Topic lock: {session.current_topic or 'Current Topic'}"
        )

        if session.next_system_note:
            system_notes.append(session.next_system_note)

        system_note = "\n".join(system_notes)

        return (
            f"{system_note}\n\n"
            f"{resolved_system_prompt}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- chapter_name: {session.chapter_name}\n"
            f"- current_topic: {session.current_topic or 'unknown'}\n\n"
            f"CONVERSATION TRANSCRIPT:\n{user_message}\n\n"
            f"HIDDEN INSTRUCTION:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only. Top-level keys must be EXACTLY:\n"
            '1) "spoken_response": string (REQUIRED and non-empty; this text will be spoken as tutor voice)\n'
            '2) "whiteboard_actions": array of action objects (CRITICAL: You MUST use the exact action name "draw_text" for ALL math equations and text! Do NOT use "write_equation")\n'
            '3) "widget": object or null. Include this ONLY if a diagram/graph is needed to explain the math. Schema: {"type": "graph"|"venn"|"number_line", "props": {...}}\n'
            '4) "advance_topic": boolean (Set to true ONLY if the topic is fully complete and it is time to move to the next topic on the agenda. Otherwise false.)\n'
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
        spoken_response = payload.get("spoken_response", "")
        whiteboard_actions = payload.get("whiteboard_actions", [])
        advance_topic = payload.get("advance_topic", False)
        widget = payload.get("widget", None)

        if not isinstance(whiteboard_actions, list):
            whiteboard_actions = []

        return {
            "spoken_response": spoken_response,
            "whiteboard_actions": self._sanitize_whiteboard_actions(whiteboard_actions),
            "widget": widget,
            "advance_topic": bool(advance_topic),
        }

    def _load_json_object(self, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        
        # 1. Quick grab if it's perfectly formatted markdown
        if "```json" in text and "```" in text.split("```json")[-1]:
            try:
                block = text.split("```json")[1].split("```")[0]
                return json.loads(block)
            except Exception:
                pass
                
        if "```" in text:
            try:
                block = text.split("```")[1]
                return json.loads(block)
            except Exception:
                pass
        
        # 2. Brute Force: Grab everything between { and }
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except Exception:
            pass
            
        # 3. Ultimate Fallback
        return self._extract_loose_fields(text)

    def _extract_loose_fields(self, text: str) -> dict[str, Any]:
        result = {"advance_topic": False, "spoken_response": "", "whiteboard_actions": [], "widget": None}
        if '"advance_topic": true' in text.lower() or '"advance_topic":true' in text.lower():
            result["advance_topic"] = True
        if text and "{" not in text:
            result["spoken_response"] = text.strip()
        return result

    def _sanitize_whiteboard_actions(self, actions: list[Any]) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict): continue
            
            # Convert everything to 'draw_text' so the frontend can actually render it!
            clean_action: dict[str, Any] = {"action": "draw_text"}
            content_value = action.get("content") or action.get("text") or action.get("value")
            if isinstance(content_value, str) and content_value.strip(): clean_action["content"] = content_value.strip()
            
            if "content" not in clean_action: continue
            sanitized.append(clean_action)
        return sanitized

    def _fallback_whiteboard_actions(self, spoken_response: str) -> list[dict[str, Any]]:
        if not isinstance(spoken_response, str) or not spoken_response.strip(): return []
        lines = [line.strip() for line in re.split(r"[\n\.]+", spoken_response) if line.strip()]
        snippets = lines[:3] if lines else [spoken_response.strip()]
        return [{"action": "draw_text", "content": snippet} for snippet in snippets]

    def _spoken_from_actions(self, actions: list[dict[str, Any]], fallback_topic: str | None = None) -> str:
        lines: list[str] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            text = str(action.get("content") or action.get("text") or action.get("value") or "").strip()
            if text:
                lines.append(text)
            if len(lines) >= 4:
                break
        if lines:
            return " ".join(lines)
        topic = str(fallback_topic or "this concept").strip()
        return (
            f"We finished the current board steps for {topic}. "
            "Click Next when you are ready for the next explanation."
        )
