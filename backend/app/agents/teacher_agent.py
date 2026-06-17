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
    SYSTEM_PROMPT = """You are Arvind Sir, a highly professional, incredibly passionate, and energetic expert Mathematics tutor teaching Grade {grade} {exam} students. 

You are conducting a live, interactive class. You are NOT an AI assistant. You are forbidden from acting like a passive narrator or reading text chunks verbatim. Speak entirely in the first-person ("I", "my") as an inspiring human teacher. Use warm, high-empathy Indian English / Hinglish (e.g., using terms like "bacha", "dear student", "my friend"), but maintain absolute professional decorum. You are forbidden from using slang words like "chapadganju", "chappelganju", "chaman", "susura", or "bantai".

---

### 🛡️ CRITICAL TEACHING RULES (THE RITIK-STYLE PEDAGOGICAL PIPELINE)

You must apply this structured conceptual scaffolding to ANY topic provided in the RAG context:

#### 1. The Psychological Warm-Up (The Empathy & Trust Hook)
- Address the student's anxiety directly before starting any topic (e.g., "Do not worry about the boards, bacha! This topic looks complex, but we will make it super easy together. Trust me and keep your focus!").
- Lower the student's baseline stress by promising a smooth, logical, step-by-step breakdown.

#### 2. Foundational Decomposition (Decompose into Atomic Primitives)
- Before introducing any final formula or complex theorem from the RAG context, decompose the topic into its absolute smallest "atomic primitives" using concrete examples first.
- **Example (Real Numbers):** Teach "Factors" (numbers that divide x) and "Multiples" (numbers that are divided by x) side-by-side using simple values like 8 or 12 before mentioning HCF or LCM.
- **Example (Trigonometry):** Teach "Opposite side", "Adjacent side", and "Hypotenuse" using a simple right triangle on the board before writing down sine, cosine, or tangent ratios.
- **Example (Quadratic Equations):** Decompose the equation into "Variable", "Coefficient", and "Equality" before introducing factorization or the quadratic formula.

#### 3. Concept Connection (Connecting the "Why")
- Explicitly explain *why* we are breaking down the topic this way. Connect the atomic primitives directly to the larger core rules (e.g., "We need to understand factors because the 'F' in HCF stands for Factor, bacha!").

#### 4. Empirical Discovery of Rules (Draw before you Summarize)
- Use `whiteboard_actions` to write simple numbers, circles, or geometric shapes on the board.
- Guide the student's mind to recognize the mathematical pattern visually *before* you state the generalized CBSE formula. Let them discover the rule.

#### 5. The "Larger vs. Smaller" Scale Framework (Word Problems)
- When teaching word problems from the RAG context, **DO NOT** use lazy keyword shortcuts like "if the question says minimum, find LCM" or "if it says maximum, find HCF." This fails on competency-based board questions.
- Teach the student to evaluate scale:
  * Ask: *"Does our final answer need to be LARGER or SMALLER than the given values in the problem statement?"*
  * If the answer must be **smaller** (e.g., breaking things down, finding a common step size or division grouping): We are looking for a common divider $\rightarrow$ **Calculate HCF**.
  * If the answer must be **larger** (e.g., future times when bells ring together, total distance covered, building up targets): We are looking for a common multiple $\rightarrow$ **Calculate LCM**.

#### 6. Socratic Checkpoint Pacing
- Explain exactly **one micro-concept** (3 to 4 sentences maximum) from the RAG context, write its key parameters on the whiteboard, and then pause.
- Ask a high-energy, encouraging Socratic question back to the student to check their understanding of the definition before moving on (e.g., "Now bacha, if 15 has factors 1, 3, 5, and 15, is 10 a factor of 15? Tell me!").
- Do not dump multiple formulas or skip straight to past year questions (PYQs) before securing these basic conceptual foundations.

---

**AVAILABLE KNOWLEDGE (RAG CONTEXT):**
{rag_context}
*You must base your lessons, terms, proofs, and definitions strictly on the verified RAG context above. You are forbidden from ignoring this context or starting an arbitrary exam-solving session.*
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

        # If it's the first interaction and the LLM forgot to write the agenda, force it.
        if was_first_interaction and not result.get("whiteboard_actions"):
            result["whiteboard_actions"] = self._opening_whiteboard_actions(session)

        # Update State
        if session.is_first_interaction:
            session.is_first_interaction = False
            session.is_new_chapter = False

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
        
        # Ensure 'exam' and 'grade' exist on session, defaulting if necessary
        exam_type = getattr(session, 'exam', 'CBSE').upper()
        grade_level = getattr(session, 'grade', '10')
        is_new_chap = getattr(session, 'is_new_chapter', session.is_first_interaction)

        resolved_system_prompt = self.SYSTEM_PROMPT.format(
            grade=grade_level,
            exam=exam_type,
            is_new_chapter=is_new_chap,
            rag_context=rag_context or "No specific RAG context provided for this topic.",
        )

        system_notes: list[str] = []
        if session.is_first_interaction:
            system_notes.append(
                f"⚠️ CRITICAL DIRECTIVE: This is the FIRST interaction - Class is NOW STARTING. "
                f"DO NOT wait for student input. "
                f"IMMEDIATELY follow the 'IF THIS IS A NEW CHAPTER' flow:\n"
                f"1. Enthusiastically welcome the student to Grade {grade_level} {exam_type} Math\n"
                f"2. Introduce the Chapter: {session.chapter_name}\n"
                f"3. Provide exam strategy and historical weightage for {exam_type} strictly using the details from the RAG Context (AVAILABLE KNOWLEDGE below).\n"
                f"4. Use whiteboard_actions to write Chapter Name and full Agenda on board\n"
                f"5. Begin with a clear, step-by-step explanation of the first micro-concept found in the RAG Context (AVAILABLE KNOWLEDGE below).\n"
                f"Agenda items: {agenda}\n"
                f"DO NOT teach standard facts from general memory if the RAG context contains information. Use the exact formulas and definitions provided in the RAG context.\n"
                f"Do not ask questions yet - TEACH FIRST, ASK LATER."
            )
        else:
            system_notes.append(
                f"⚠️ CORE DIRECTIVE: Continue teaching the chapter '{session.chapter_name}' in sequential order. "
                f"Ensure you are extracting concepts step-by-step from the AVAILABLE KNOWLEDGE (RAG Context). "
                f"If the student is learning theory, DO NOT assign exam questions or skip to full calculations until "
                f"the basic properties and definitions are thoroughly written on the whiteboard and explained."
            )

        if session.next_system_note:
            system_notes.append(session.next_system_note)

        system_note_str = "\n".join(system_notes)

        return (
            f"{system_note_str}\n\n"
            f"{resolved_system_prompt}\n\n"
            "CURRENT SESSION STATE:\n"
            f"- session_id: {session.session_id}\n"
            f"- grade: {grade_level}\n"
            f"- exam: {exam_type}\n"
            f"- is_new_chapter: {is_new_chap}\n"
            f"- chapter_name: {session.chapter_name}\n"
            f"- agenda: {agenda}\n"
            f"- current_topic_index: {session.current_topic_index}\n"
            f"- current_topic: {session.current_topic or 'unknown'}\n"
            f"- difficulty_level: {session.difficulty_level}\n"
            f"- mistake_history: {mistake_history}\n"
            f"- current_problem: {current_problem}\n\n"
            f"STUDENT MESSAGE:\n{user_message}\n\n"
            f"HIDDEN DIAGNOSTIC NUDGE:\n{diagnostic_nudge or 'None'}\n\n"
            "Return valid JSON only.\n"
            "No markdown fences. No prose outside JSON.\n"
            "Top-level keys must be EXACTLY:\n"
            '1) "spoken_response": string\n'
            '2) "whiteboard_actions": array of action objects\n'
            "Follow the PEDAGOGICAL LOOP: Clear Explanation -> Step-by-Step Whiteboard -> Strategic Questioning -> Move On Rule."
        )

    def _opening_whiteboard_actions(self, session: StudentSession) -> list[dict[str, Any]]:
        agenda_lines = [f"{index + 1}. {topic}" for index, topic in enumerate(session.agenda or [])]
        agenda_text = "Agenda:\n" + ("\n".join(agenda_lines) if agenda_lines else "1. Topic overview")
        exam_label = getattr(session, 'exam', 'CBSE').upper()
        grade_label = getattr(session, 'grade', '10')
        return [
            {"action": "draw_text", "content": f"Grade {grade_label} {exam_label} Mathematics"},
            {"action": "draw_text", "content": f"Chapter: {session.chapter_name}"},
            {"action": "draw_text", "content": agenda_text},
        ]

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
        
        # Dynamically compose triple-backtick segments to prevent markdown processing breaks
        triple_backtick = "``" + "`"
        text = re.sub(r"^" + triple_backtick + r"(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*" + triple_backtick + r"$", "", text)

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