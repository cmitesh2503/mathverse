from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from ..models.session import StudentSession
from ..services.ai_gateway import generate_response
from ..services.rag_service import retrieve_context


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
    DEFAULT_CONFIGURATION: dict[str, Any] = {
        "default_exam": "cbse",
        "default_grade": 10,
        "default_phase": "teaching",
        "default_chapter_label": "Mathematics Overview",
        "default_topic_label": "Mathematics",
        "default_difficulty_level": "moderate",
        "default_session_id": "live-session",
        "default_teaching_language": "en-IN",
        "default_rag_k": 8,
        "missing_rag_context_label": "No specific RAG context provided for this topic.",
    }

    def __init__(self, configuration: dict[str, Any] | None = None) -> None:
        merged = dict(self.DEFAULT_CONFIGURATION)
        if isinstance(configuration, dict):
            merged.update(configuration)
        self.configuration = merged

    def _config(self, key: str, fallback: Any = None) -> Any:
        if key in self.configuration:
            return self.configuration[key]
        return fallback

    def _session_value(self, session: Any, attr: str, default: Any = None) -> Any:
        if isinstance(session, dict):
            return session.get(attr, default)
        return getattr(session, attr, default)

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _resolve_current_chapter(self, session: Any) -> str:
        raw = self._session_value(session, "current_chapter")
        if not str(raw or "").strip():
            raw = self._session_value(session, "chapter_name")
        return str(raw or "").strip()

    def _resolve_current_phase(self, session: Any) -> str:
        raw = self._session_value(session, "current_phase")
        if raw is None:
            raw = self._session_value(session, "active_phase", self._config("default_phase", "teaching"))
        resolved = str(getattr(raw, "value", raw) or "").strip().lower()
        if resolved:
            return resolved
        return str(self._config("default_phase", "teaching")).strip().lower() or "teaching"

    def _resolve_current_lesson_topic(self, session: Any, user_message: str) -> str:
        topic = str(self._session_value(session, "current_topic", "") or "").strip()
        if topic:
            return topic
        chapter = self._resolve_current_chapter(session)
        if chapter:
            return chapter
        fallback = str(user_message or "").strip()
        if fallback:
            return fallback
        return str(self._config("default_topic_label", "Mathematics")).strip() or "Mathematics"

    def _build_session_rag_context(self, session: Any, user_message: str) -> str:
        current_lesson_topic = self._resolve_current_lesson_topic(session, user_message)
        current_chapter = self._resolve_current_chapter(session)
        current_phase = self._resolve_current_phase(session)
        exam_type = str(self._session_value(session, "exam", self._config("default_exam", "cbse"))).strip().lower() or "cbse"
        grade = self._coerce_int(self._session_value(session, "grade", self._config("default_grade", 10)), 10)
        target_k = max(1, self._coerce_int(self._config("default_rag_k", 8), 8))

        chapter_filter: str | None = current_chapter or None
        if chapter_filter is None:
            print("WARNING: session.current_chapter is empty. Retrieving RAG context across all chapters.")

        context = retrieve_context(
            query=current_lesson_topic,
            chapter=chapter_filter,
            phase=current_phase,
            exam_type=exam_type,
            k=target_k,
            grade=grade,
        )
        return str(context or "").strip()

    @staticmethod
    def _render_system_prompt(template: str, **values: Any) -> str:
        """Safely format known placeholders while keeping literal JSON braces intact."""
        escaped = template.replace("{", "{{").replace("}", "}}")
        for key in values:
            escaped = escaped.replace(f"{{{{{key}}}}}", f"{{{key}}}")
        return escaped.format(**values)

    SYSTEM_PROMPT = """You are Arvind Sir, a highly professional, expert Mathematics tutor for Grade {grade} {exam} students.

**AVAILABLE KNOWLEDGE (RAG CONTEXT):**
{rag_context}
*You MUST base your syllabus, weightage, and problems strictly on the information provided above.*
CURRENT PHASE: {phase}. Do not jump to solving problems or skipping theory until the engine issues a 'phase_transition' command.

**LANGUAGE STYLE:**
Reply in Hindi/Hinglish for spoken explanations, but keep all mathematics vocabulary in English.
Do not translate terms like probability, outcome, sample space, event, formula, theorem, equation,
numerator, denominator, factor, HCF, LCM, triangle, coordinate, chapter names, symbols, and formulas.
For whiteboard_actions, you MUST use actual mathematical symbols (e.g., √, π, ×, ÷, ^, °) instead of words like sqrt or pi.
For spoken_response, you MUST spell out symbols in words so the voice engine pronounces them correctly (e.g., write "square root" instead of "sqrt", "squared" instead of "^2", "degrees" instead of "°", "pi" instead of "π").

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

5. **NCERT Figures & Diagrams:**
   - Whenever explaining a concept or exercise that has a figure in the NCERT book, use `{"action": "draw_shape", "content": "Detailed description of the NCERT figure"}` to show it on the blackboard.

**IF THE STUDENT ASKS A DOUBT OR QUESTION:**
1. Pause the planned lesson and answer the question directly.
2. If the question relates to the current problem or current topic, explain it using that exact problem/topic.
3. If the student needs a prerequisite concept first, explain that prerequisite slowly with one simple example, and then connect it back to the current problem.
4. Do not reply with vague study strategy. Use the question to produce a clear conceptual answer and a short worked example.
5. When answering a student's doubt, ALWAYS end by asking if they understood or if they need further clarification, for example: "Does that make sense?"
6. Do NOT assume the doubt is fully resolved until the student confirms it.

**THE PEDAGOGICAL LOOP (HOW YOU TEACH - GUIDED EXPLAINER):**
When teaching a topic or solving a problem, you MUST follow this sequence strictly:

1. **Read & Explain Goal FIRST:** If given a problem image or text, your VERY FIRST step is to read the problem statement out loud to the student and explicitly state what you are trying to solve. Say "First, let us read the question carefully: [Question]. Let me explain the solution step by step." Do not start calculating yet.
2. **The "Why" Before The "How":** Explain the real-world intuition or coordinate geometry mechanics before executing any mathematical rules or formulas.
3. **Step-by-Step Visualization & Construction:** Build equations and visual layouts on the board step-by-step. Let your whiteboard actions match your spoken text fluidly.
4. **Strategic Questioning:** Explain 2-3 logical steps, then pause your mathematical output and ask a clean checking question based strictly on what is currently drawn on the board (e.g., "Looking at our drawn graph, what point does the line cut across the Y-axis?").
5. **The "Move On" Rule:** If the student is stuck, wrong, or silent, do NOT loop. Say, "That's okay," explain the step clearly, write it on the board, and continue smoothly.
6. **CRITICAL ACCURACY RULE:** If the math logic is not found in the retrieved context, you are forbidden from guessing. You must state: 'I don't have the CBSE guidelines for that in my current notes, let's look at the concepts on the board.'

**MUST DECODE PROBLEM GIVEN/REQUIRED (MANDATORY):**
- Before producing any equations or algebraic manipulations on the whiteboard, you MUST explicitly decode the problem into two separate `write_text` whiteboard actions in this exact order:
    1. `{"action": "write_text", "x": <num>, "y": <num>, "label": "What is given: <succinct list of givens>", "color": "black"}`
    2. `{"action": "write_text", "x": <num>, "y": <num>, "label": "What needs to be found: <succinct target>", "color": "black"}`
    The `What is given` and `What needs to be found` entries MUST appear before any `write_text` that contains an equation (a string with `=`) or before any `draw_line`/`draw_angle` that constructs the main geometry for the solution. Failing to include these two explicit decode actions is a protocol violation.

**STRICT WHITEBOARD JSON ACTIONS SCHEMA (MANDATORY):**
Only use the following action names and properties. Do NOT invent new top-level action names or arbitrary nested keys — the frontend will reject unknown keys.

- `draw_line`: draw a line segment
    Required properties: `action` ("draw_line"), `x1` (number), `y1` (number), `x2` (number), `y2` (number)
    Optional properties: `color` (string), `thickness` (number), `label` (string)
    Example: {"action":"draw_line","x1":10,"y1":20,"x2":100,"y2":20,"color":"black","thickness":2}

- `draw_angle`: draw an angle arc
    Required properties: `action` ("draw_angle"), `x` (number), `y` (number), `radius` (number), `start_angle` (number), `end_angle` (number)
    Optional properties: `label` (string), `color` (string)
    Example: {"action":"draw_angle","x":50,"y":60,"radius":20,"start_angle":0,"end_angle":30,"label":"θ","color":"black"}

- `write_text`: place a text label on board (use for problem statements, givens, equations)
    Required properties: `action` ("write_text"), `x` (number), `y` (number), `label` (string)
    Optional properties: `font_size` (number), `color` (string)
    Example: {"action":"write_text","x":120,"y":40,"label":"What is given: a=5","font_size":14,"color":"black"}

- `highlight_element`: highlight a region or element on the board
    Required properties: `action` ("highlight_element"), `x1` (number), `y1` (number), `x2` (number), `y2` (number), `color` (string)
    Optional properties: `label` (string), `opacity` (number)
    Example: {"action":"highlight_element","x1":10,"y1":10,"x2":100,"y2":50,"color":"green","label":"target"}

ADDITIONAL RULES:
- Maintain ordering: the decode pair (`What is given` / `What needs to be found`) MUST precede any equation-writing or geometry-building actions.
- Do not output `draw_shape`, `draw_text` (legacy), `diagram` or any other action names unless you map them to the strict schema above.
- If a single visual requires multiple primitive actions, emit them in the natural construction order (e.g., lines first, then angles, then labels, then highlights).
- Always ensure coordinates are integers or floats and relative to the same board coordinate system.
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
        session_rag_context = await asyncio.to_thread(self._build_session_rag_context, session, user_message)
        provided_rag_context = str(rag_context or "").strip()
        resolved_rag_context = session_rag_context
        if provided_rag_context and session_rag_context:
            if session_rag_context in provided_rag_context:
                resolved_rag_context = provided_rag_context
            else:
                resolved_rag_context = f"{provided_rag_context}\n\n{session_rag_context}".strip()
        elif provided_rag_context:
            resolved_rag_context = provided_rag_context

        prompt = self._build_prompt(
            session,
            user_message,
            diagnostic_nudge,
            rag_context=resolved_rag_context,
        )
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
        current_problem = json.dumps(self._session_value(session, "current_problem", {}), ensure_ascii=False)
        mistake_history = json.dumps(self._session_value(session, "mistake_history", []), ensure_ascii=False)
        agenda = json.dumps(self._session_value(session, "agenda", []), ensure_ascii=False)
        recent_transcript = self._recent_transcript_context(session)
        
        exam_type = str(self._session_value(session, "exam", self._config("default_exam", "cbse"))).upper()
        grade_level = str(self._session_value(session, "grade", self._config("default_grade", 10)))
        teaching_language = _normalize_teaching_language(
            self._session_value(session, "teaching_language", self._config("default_teaching_language", "en-IN"))
        )
        phase = self._resolve_current_phase(session)
        
        is_first_interaction = bool(self._session_value(session, "is_first_interaction", False))
        is_new_chap = bool(self._session_value(session, "is_new_chapter", is_first_interaction))
        
        chapter_title = self._resolve_current_chapter(session) or str(
            self._config("default_chapter_label", "Mathematics Overview")
        )
        current_topic = str(
            self._session_value(
                session,
                "current_topic",
                chapter_title or self._config("default_topic_label", "Mathematics"),
            )
            or chapter_title
            or self._config("default_topic_label", "Mathematics")
        )

        resolved_system_prompt = self._render_system_prompt(
            self.SYSTEM_PROMPT,
            grade=grade_level,
            exam=exam_type,
            is_new_chapter=is_new_chap,
            chapter_name=chapter_title,
            current_topic=current_topic,
            rag_context=rag_context or self._config("missing_rag_context_label", "No specific RAG context provided for this topic."),
            phase=phase,
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

        next_note = self._session_value(session, "next_system_note")
        if next_note:
            system_notes.append(str(next_note))

        system_note_str = "\n".join(system_notes)

        return (
            f"{system_note_str}\n\n"
            f"{resolved_system_prompt}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- session_id: {self._session_value(session, 'session_id', self._config('default_session_id', 'live-session'))}\n"
            f"- grade: {grade_level}\n"
            f"- exam: {exam_type}\n"
            f"- is_new_chapter: {is_new_chap}\n"
            f"- chapter_name: {chapter_title}\n"
            f"- agenda: {agenda}\n"
            f"- current_topic_index: {self._session_value(session, 'current_topic_index', 0)}\n"
            f"- current_topic: {current_topic}\n"
            f"- difficulty_level: {self._session_value(session, 'difficulty_level', self._config('default_difficulty_level', 'moderate'))}\n"
            f"- mistake_history: {mistake_history}\n"
            f"- current_problem: {current_problem}\n"
            f"- recent_transcript:\n{recent_transcript or 'No saved transcript yet.'}\n\n"
            f"STUDENT MESSAGE / PROBLEM STATEMENT:\n{user_message}\n\n"
            f"HIDDEN DIAGNOSTIC NUDGE:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only.\n"
            "No markdown fences. No prose outside JSON.\n"
            "Top-level keys must be EXACTLY:\n"
            '1) "internal_reasoning": string (Use this scratchpad to solve the math step-by-step before the spoken output)\n'
            '2) "spoken_response": string\n'
            '3) "whiteboard_actions": list\n'
            "Follow the PEDAGOGICAL LOOP: Acknowledge Problem -> Explain the 'Why' -> Step-by-Step Whiteboard -> Strategic Questioning -> Move On Rule."
        )

    def _opening_whiteboard_actions(self, session: StudentSession) -> list[dict[str, Any]]:
        agenda_lines = [f"{index + 1}. {topic}" for index, topic in enumerate(session.agenda or [])]
        agenda_text = "Agenda:\n" + ("\n".join(agenda_lines) if agenda_lines else "1. Topic overview")
        exam_label = str(getattr(session, "exam", self._config("default_exam", "cbse"))).upper()
        chapter_label = self._resolve_current_chapter(session) or str(
            self._config("default_chapter_label", "Current Chapter")
        )
        return [
            {"action": "draw_text", "content": f"Grade {session.grade} {exam_label} Mathematics"},
            {"action": "draw_text", "content": f"Chapter: {chapter_label}"},
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

    def _recent_transcript_context(self, session: Any) -> str:
        transcript = self._session_value(session, "transcript", [])
        if not isinstance(transcript, list):
            return ""

        lines: list[str] = []
        for turn in transcript[-8:]:
            if isinstance(turn, dict):
                role = str(turn.get("role") or "").strip()
                content = str(turn.get("content") or "").strip()
            else:
                role = str(getattr(turn, "role", "") or "").strip()
                content = str(getattr(turn, "content", "") or "").strip()
            if role and content:
                lines.append(f"{role.title()}: {content}")
        return "\n".join(lines)

    def _sanitize_whiteboard_actions(self, actions: list[Any]) -> list[dict[str, Any]]:
        """Validate and map incoming LLM whiteboard actions to the strict frontend schema.

        Allowed canonical actions:
        - draw_line: {action, x1, y1, x2, y2, [color], [thickness], [label]}
        - draw_angle: {action, x, y, radius, start_angle, end_angle, [label], [color]}
        - write_text: {action, x, y, label, [font_size], [color]}
        - highlight_element: {action, x1, y1, x2, y2, color, [label], [opacity]}

        This function maps legacy names where possible, while preserving
        drawable figure actions needed by the current frontend.
        """
        sanitized: list[dict[str, Any]] = []
        y_cursor = 20
        def to_number(v, default=0):
            try:
                return int(v) if isinstance(v, int) or (isinstance(v, str) and v.isdigit()) else float(v)
            except Exception:
                try:
                    return float(v)
                except Exception:
                    return default

        for raw in actions or []:
            if not isinstance(raw, dict):
                continue
            action_name = str(raw.get("action") or raw.get("type") or "").strip().lower()

            # Normalize legacy or alternative names
            if action_name in {"draw_text", "drawtext", "text", "write_text_legacy", "diagram"}:
                action_name = "write_text"
            if action_name in {"draw_shape", "shape"}:
                action_name = "draw_shape"
            if action_name in {"drawline", "line"}:
                action_name = "draw_line"
            if action_name in {"drawangle", "angle"}:
                action_name = "draw_angle"
            if action_name in {"highlight", "highlightarea"}:
                action_name = "highlight_element"

            if action_name == "draw_shape":
                content = raw.get("content") or raw.get("label") or raw.get("text") or raw.get("value")
                if not isinstance(content, str) or not content.strip():
                    continue
                sanitized.append({"action": "draw_shape", "content": content.strip()})
                continue

            if action_name == "write_text":
                label = raw.get("label") or raw.get("content") or raw.get("text") or raw.get("value")
                if not isinstance(label, str) or not label.strip():
                    continue
                x = to_number(raw.get("x"), default=10)
                y = to_number(raw.get("y"), default=y_cursor)
                y_cursor += 20
                clean = {"action": "write_text", "x": x, "y": y, "label": label.strip()}
                if raw.get("font_size") is not None:
                    clean["font_size"] = to_number(raw.get("font_size"), default=14)
                if raw.get("color"):
                    clean["color"] = str(raw.get("color"))
                sanitized.append(clean)
                continue

            if action_name == "draw_line":
                x1 = raw.get("x1")
                y1 = raw.get("y1")
                x2 = raw.get("x2")
                y2 = raw.get("y2")
                if None in (x1, y1, x2, y2):
                    # try alternate keys
                    x1 = raw.get("x") or raw.get("x_start")
                    y1 = raw.get("y") or raw.get("y_start")
                    x2 = raw.get("x_end") or raw.get("x2")
                    y2 = raw.get("y_end") or raw.get("y2")
                if None in (x1, y1, x2, y2):
                    continue
                clean = {
                    "action": "draw_line",
                    "x1": to_number(x1),
                    "y1": to_number(y1),
                    "x2": to_number(x2),
                    "y2": to_number(y2),
                }
                if raw.get("color"):
                    clean["color"] = str(raw.get("color"))
                if raw.get("thickness") is not None:
                    clean["thickness"] = to_number(raw.get("thickness"), default=1)
                if raw.get("label"):
                    clean["label"] = str(raw.get("label"))
                sanitized.append(clean)
                continue

            if action_name == "draw_angle":
                x = raw.get("x")
                y = raw.get("y")
                radius = raw.get("radius")
                start_angle = raw.get("start_angle")
                end_angle = raw.get("end_angle")
                if None in (x, y, radius, start_angle, end_angle):
                    continue
                clean = {
                    "action": "draw_angle",
                    "x": to_number(x),
                    "y": to_number(y),
                    "radius": to_number(radius),
                    "start_angle": to_number(start_angle),
                    "end_angle": to_number(end_angle),
                }
                if raw.get("label"):
                    clean["label"] = str(raw.get("label"))
                if raw.get("color"):
                    clean["color"] = str(raw.get("color"))
                sanitized.append(clean)
                continue

            if action_name == "highlight_element":
                x1 = raw.get("x1") or raw.get("x")
                y1 = raw.get("y1") or raw.get("y")
                x2 = raw.get("x2") or raw.get("width") or raw.get("x_end")
                y2 = raw.get("y2") or raw.get("height") or raw.get("y_end")
                color = raw.get("color") or raw.get("fill")
                if None in (x1, y1, x2, y2) or not color:
                    continue
                clean = {
                    "action": "highlight_element",
                    "x1": to_number(x1),
                    "y1": to_number(y1),
                    "x2": to_number(x2),
                    "y2": to_number(y2),
                    "color": str(color),
                }
                if raw.get("label"):
                    clean["label"] = str(raw.get("label"))
                if raw.get("opacity") is not None:
                    clean["opacity"] = to_number(raw.get("opacity"), default=0.5)
                sanitized.append(clean)
                continue

            # Unknown actions are ignored — keep the whiteboard safe and predictable
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
