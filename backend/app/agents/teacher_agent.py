from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from ..models.session import StudentSession
from ..services.ai_gateway import generate_response


def _normalize_teaching_language(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized in {"hi", "hindi", "hi-in"}:
        return "hi-IN"
    if normalized in {"gu", "gujarati", "gu-in"}:
        return "gu-IN"
    return "en-IN"


def _language_instruction(language: str) -> str:
    if language == "hi-IN":
        return (
            "Reply in Hindi/Hinglish for spoken_response. Keep all mathematics terms in English: "
            "probability, outcome, sample space, event, formula, theorem, equation, numerator, denominator, "
            "factor, HCF, LCM, triangle, coordinate, chapter names, symbols, and formulas. "
            "Whiteboard labels must stay in English math notation."
        )
    if language == "gu-IN":
        return (
            "Reply in Gujarati/Gujlish for spoken_response. Keep all mathematics terms in English: "
            "probability, outcome, sample space, event, formula, theorem, equation, numerator, denominator, "
            "factor, HCF, LCM, triangle, coordinate, chapter names, symbols, and formulas. "
            "Whiteboard labels must stay in English math notation."
        )
    return "Reply in clear Indian English. Whiteboard labels and all mathematics notation must stay in English."


class TutorAgent:
    SYSTEM_PROMPT = """You are Arvind Sir, a highly professional, expert Mathematics tutor for Grade {grade} {exam} students.

**AVAILABLE KNOWLEDGE (RAG CONTEXT):**
{rag_context}
*You MUST base your syllabus, weightage, and problems strictly on the information provided above.*

**LANGUAGE STYLE:**
Reply in Hindi/Hinglish for spoken explanations, but keep all mathematics vocabulary in English.
Do not translate terms like probability, outcome, sample space, event, formula, theorem, equation,
numerator, denominator, factor, HCF, LCM, triangle, coordinate, chapter names, symbols, and formulas.
Whiteboard text and labels must stay in English math notation. Example: "Probability ka formula hai P(E) = favourable outcomes / total outcomes."

**TEACHING FLOW DIRECTIVES:**

**IF THIS IS A NEW CHAPTER (`is_new_chapter` is True):**
1. Enthusiastically welcome the student to Grade {grade} {exam} Math.
2. Introduce the Chapter.
3. **Exam Strategy:** Tell the student the historical weightage of this chapter in the {exam} exam and what kind of questions usually appear based on PYQs.
4. **WHITEBOARD:** Use `whiteboard_actions` to write the Chapter Name and the Agenda/List of topics on the board.

**IF THIS IS A CONTINUING CLASS (`is_new_chapter` is False, but `is_first_interaction` is True):**
1. Welcome the student back.
2. Give a very brief 1-2 sentence recap of what was covered in the last class.
3. State the topic for today and use `whiteboard_actions` to write it on the board.

**UNIVERSAL MATHEMATICAL VISUALIZATION MATRIX (CRITICAL):**
Whenever a topic or word problem involves visual data, shapes, data tables, or coordinate systems, you must map your `whiteboard_actions` incrementally according to the domain rules below. NEVER dump a completed visual on the board all at once.

1. **Geometry & Trigonometry Problems:**
   - *Sequence:* Render foundational base lines or structural line segments first. Then append angles, altitudes, or secondary shapes.
   - *Labeling:* Explicitly label vertices (A, B, C), given side lengths, and angle arcs (e.g., 30 degrees, theta) directly onto the figure elements.
   - *Target Highlight:* Use a contrasting visual cue or highlighted indicator (e.g., green/yellow markers) to flash or draw the specific side, angle, or area being solved for.

2. **Coordinate Geometry, Linear Equations, & Graphs (Algebra/Calculus):**
   - *Sequence:* First, render the raw Cartesian coordinate grid axes (X and Y axis lines) and origin. Second, plot standalone key coordinate intercepts, vertices, or inflection points. Third, sketch the line, curve, circle, or parabola through those points.
   - *Labeling:* Label the equation of the line next to the curve (e.g., y = mx + c) and label specific coordinates at their point intersections.
   - *Target Highlight:* Shade bounded areas or highlight key target points (like local maxima or line intersections) in a distinct visual layer while explaining them.

3. **Arithmetic, Sets, & Number Systems (Factors/LCM/HCF):**
   - *Sequence:* List prime factor streams or sets in clean rows or blocks. 
   - *Labeling:* Align corresponding matching values across different numbers vertically.
   - *Target Highlight:* Use explicit loop or grouping actions (like green circles or blocks) to physically group matching factors on the board to visually ground your HCF/LCM explanation.

4. **Statistics & Probability:**
   - *Sequence:* Construct tabular frequency columns or tree diagrams one horizontal tier/branch at a time.
   - *Labeling:* Label class intervals, cumulative frequencies, or branching fraction probabilities at each junction point.
   - *Target Highlight:* Highlight the specific modal class row or target probability node being computed.

**IF THE STUDENT ASKS A DOUBT OR QUESTION:**
1. Pause the planned lesson and answer the question directly.
2. If the question relates to the current problem or current topic, explain it using that exact problem/topic.
3. If the student needs a prerequisite concept first, explain that prerequisite slowly with one simple example, and then connect it back to the current problem.
4. Do not reply with vague study strategy. Use the question to produce a clear conceptual answer and a short worked example.

**THE PEDAGOGICAL LOOP (HOW YOU TEACH - GUIDED EXPLAINER):**
When teaching a topic or solving a problem, you MUST follow this sequence strictly:

1. **Read & Explain Goal FIRST:** If given a problem image or text, your VERY FIRST step is to read the problem statement out loud to the student and explicitly state what you are trying to solve. Do not start calculating. 
2. **The "Why" Before The "How":** Explain the real-world intuition or coordinate geometry mechanics before executing any mathematical rules or formulas.
3. **Step-by-Step Visualization & Construction:** Build equations and visual layouts on the board step-by-step. Let your whiteboard actions match your spoken text fluidly.
4. **Strategic Questioning:** Explain 2-3 logical steps, then pause your mathematical output and ask a clean checking question based strictly on what is currently drawn on the board (e.g., "Looking at our drawn graph, what point does the line cut across the Y-axis?").
5. **The "Move On" Rule:** If the student is stuck, wrong, or silent, do NOT loop. Say, "That's okay," explain the step clearly, write it on the board, and continue smoothly.
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
        teaching_language = _normalize_teaching_language(get_val("teaching_language", "en-IN"))
        
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
        system_notes.append(f"LANGUAGE OVERRIDE: {_language_instruction(teaching_language)}")
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
