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
7. Problem Reading (MANDATORY): Always read out "Problem no" and the full problem statement first, then explain what is asked.
8. Complex Problems (MANDATORY): For multi-part or complex questions, split into mini-parts (Part A, Part B, ...) and draw each sub-step using 'draw_text' before moving to the next.
9. Human Tutoring Rule 1 - Acknowledge the Problem: Before solving, restate what the student is being asked to find in simple words.
10. Human Tutoring Rule 2 - Why Before How: Before calculation steps, explain the physical/logical reason for choosing the method (e.g., sync events -> LCM, part-whole relation -> equation), then perform algebra.
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
        session: Any,
        user_message: str,
        diagnostic_nudge: str | None,
        rag_context: str,
    ) -> str:
        # Robust context extractor handling both class model instances and standard dictionaries
        def get_val(attr: str, default: Any = None) -> Any:
            if isinstance(session, dict):
                return session.get(attr, default)
            return getattr(session, attr, default)

        current_problem = json.dumps(get_val("current_problem", {}), ensure_ascii=False)
        mistake_history = json.dumps(get_val("mistake_history", []), ensure_ascii=False)
        agenda = json.dumps(get_val("agenda", []), ensure_ascii=False)
        
        exam_type = str(get_val("exam", "CBSE")).upper()
        grade_level = str(get_val("grade", "10"))
        
        is_first_interaction = bool(get_val("is_first_interaction", False))
        is_new_chap = bool(get_val("is_new_chapter", is_first_interaction))
        
        # Robust fallbacks to stop WebSocket/API KeyError/AttributeError crashes
        chapter_title = str(get_val("chapter_name", "Mathematics Overview"))
        current_topic = str(get_val("current_topic", chapter_title) or chapter_title)

        resolved_system_prompt = self.SYSTEM_PROMPT.format(
            grade=grade_level,
            exam=exam_type,
            is_new_chapter=is_new_chap,
            chapter_name=chapter_title,
            current_topic=current_topic,
            rag_context=rag_context or "No specific RAG context provided for this topic.",
        )

        system_notes: list[str] = []
        if is_first_interaction:
            system_notes.append(
                f"⚠️ CRITICAL DIRECTIVE: This is the FIRST interaction - Class is NOW STARTING. "
                f"DO NOT wait for student input. "
                f"IMMEDIATELY follow the 'IF THIS IS A NEW CHAPTER' flow:\n"
                f"1. Enthusiastically welcome the student to Grade {grade_level} {exam_type} Math\n"
                f"2. Introduce the Chapter: {chapter_title}\n"
                f"3. Provide exam strategy and historical weightage for {exam_type} based on the RAG context.\n"
                f"4. Use whiteboard_actions to write Chapter Name and full Agenda on board\n"
                f"5. Begin with a clear explanation of the first topic\n"
                f"Agenda items: {agenda}\n"
                f"Do not ask questions yet - TEACH FIRST, ASK LATER."
            )

        next_note = get_val("next_system_note")
        if next_note:
            system_notes.append(str(next_note))

        system_note_str = "\n".join(system_notes)

        return (
            f"{system_note_str}\n\n"
            f"{resolved_system_prompt}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- session_id: {get_val('session_id', 'live-session')}\n"
            f"- grade: {grade_level}\n"
            f"- exam: {exam_type}\n"
            f"- is_new_chapter: {is_new_chap}\n"
            f"- chapter_name: {chapter_title}\n"
            f"- agenda: {agenda}\n"
            f"- current_topic_index: {get_val('current_topic_index', 0)}\n"
            f"- current_topic: {current_topic}\n"
            f"- difficulty_level: {get_val('difficulty_level', 'medium')}\n"
            f"- mistake_history: {mistake_history}\n"
            f"- current_problem: {current_problem}\n\n"
            f"STUDENT MESSAGE / PROBLEM STATEMENT:\n{user_message}\n\n"
            f"HIDDEN DIAGNOSTIC NUDGE:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only.\n"
            "No markdown fences. No prose outside JSON.\n"
            "Top-level keys must be EXACTLY:\n"
            '1) "spoken_response": string\n'
            '2) "whiteboard_actions": array of action objects\n'
            "Follow the PEDAGOGICAL LOOP: Acknowledge Problem -> Explain the 'Why' -> Step-by-Step Whiteboard -> Strategic Questioning -> Move On Rule."
        )

    def _opening_whiteboard_actions(self, session: StudentSession) -> list[dict[str, Any]]:
        agenda_lines = [f"{index + 1}. {topic}" for index, topic in enumerate(session.agenda or [])]
        agenda_text = "Agenda:\n" + ("\n".join(agenda_lines) if agenda_lines else "1. Topic overview")
        exam_label = str(getattr(session, "exam", "CBSE")).upper()
        return [
            {"action": "draw_text", "content": f"Grade {session.grade} {exam_label} Mathematics"},
            {"action": "draw_text", "content": f"Chapter: {session.chapter_name or 'Current Chapter'}"},
            {"action": "draw_text", "content": agenda_text},
        ]

    def _parse_agent_response(self, raw_response: str) -> dict[str, Any]:
        payload = self._load_json_object(raw_response)
        spoken_response = payload.get("spoken_response", "")
        whiteboard_actions = payload.get("whiteboard_actions", [])
        advance_topic = payload.get("advance_topic", False)
        widget = payload.get("widget")

        if not isinstance(spoken_response, str):
            spoken_response = str(spoken_response or "")
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
