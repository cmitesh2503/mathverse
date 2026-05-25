from __future__ import annotations

import asyncio
import json
import re
from typing import Any

try:
    from app.models.session import SessionPhase, StudentSession
    from app.services.ai_gateway import generate_response
    from app.services.rag_service import get_context
except ModuleNotFoundError:
    from ..models.session import SessionPhase, StudentSession
    from ..services.ai_gateway import generate_response
    from ..services.rag_service import get_context


class ProctorAgent:
    WARNING_LIMIT = 2
    SYSTEM_PROMPT = (
        "YOU ARE A MULTIMODAL AI PROCTOR. You are receiving a live video feed of the student taking a JEE Main Mock Test.\n\n"
        "EXAM START PROTOCOL:\n"
        "The exam status is currently 'pending'. Do NOT generate the first question until you visually confirm the student's face "
        "is clearly visible in the camera frame.\n"
        "If you see them, say: \"Identity verified. Starting the JEE Mock Test. Good luck.\" and present the first question.\n\n"
        "ANTI-CHEAT PROTOCOL:\n"
        "Continuously monitor the video feed while they solve problems.\n"
        "Cheating Behaviors: Looking off-screen frequently, a second person entering the frame, using a mobile phone, or leaving "
        "the camera frame entirely.\n"
        "Warning System: If you detect cheating, you MUST interrupt and issue a verbal warning. Output a specific JSON command: "
        "{\"action\": \"issue_warning\", \"reason\": \"<describe what you saw>\"}.\n"
        "Termination: If the system notes that warnings_issued has reached 2, you MUST immediately end the test. Output: "
        "{\"action\": \"terminate_exam\", \"reason\": \"Maximum warnings exceeded.\"} and refuse to generate further questions.\n\n"
        "QUESTION GENERATION RULES:\n"
        "Generate a BRAND NEW JEE Main Mathematics MCQ with options A/B/C/D from provided PYQ context.\n"
        "Do not repeat exact source PYQs, do not reveal the answer in spoken text."
    )

    async def process_message(self, session: StudentSession, user_message: str) -> dict[str, Any]:
        session.active_phase = SessionPhase.TESTING
        session.current_phase = SessionPhase.TESTING.value
        message = (user_message or "").strip()

        if session.exam_status == "terminated" or session.warnings_issued >= self.WARNING_LIMIT:
            return self._terminate_exam(session, "Maximum warnings exceeded.")

        proctor_signal = await self._evaluate_proctor_signal(session, message)
        action = str(proctor_signal.get("action", "")).lower()
        reason = str(proctor_signal.get("reason", "")).strip()

        if action == "terminate_exam":
            return self._terminate_exam(session, reason or "Maximum warnings exceeded.")

        if action == "issue_warning":
            session.warnings_issued += 1
            if session.warnings_issued >= self.WARNING_LIMIT:
                return self._terminate_exam(session, "Maximum warnings exceeded.")
            warning_reason = reason or "Suspicious activity detected in the video feed."
            return {
                "spoken_response": (
                    f"Warning {session.warnings_issued}/{self.WARNING_LIMIT}: {warning_reason}. "
                    "Stay in frame and focus on the exam."
                ),
                "whiteboard_actions": [
                    {
                        "action": "issue_warning",
                        "reason": warning_reason,
                        "warnings": session.warnings_issued,
                    }
                ],
                **self._metrics(session),
            }

        if session.exam_status == "pending":
            if action == "identity_verified" or self._looks_like_identity_confirmation(message):
                session.exam_status = "running"
                first_question = await self._generate_next_question(session)
                first_question["spoken_response"] = (
                    "Identity verified. Starting the JEE Mock Test. Good luck.\n\n"
                    f"{first_question['spoken_response']}"
                )
                return first_question

            return {
                "spoken_response": (
                    "Camera verification pending. Keep your face clearly visible in the frame to start the test."
                ),
                "whiteboard_actions": [
                    {
                        "action": "await_identity_verification",
                        "reason": "Face not clearly visible yet.",
                    }
                ],
                **self._metrics(session),
            }

        answer = self._extract_option(message)
        has_active_question = bool(session.current_problem and session.current_problem.get("correct_option"))

        if has_active_question and answer:
            return await self._evaluate_and_advance(session, answer)

        return await self._generate_next_question(session)

    async def _generate_next_question(self, session: StudentSession) -> dict[str, Any]:
        if session.exam_status == "terminated":
            return self._terminate_exam(session, "Maximum warnings exceeded.")

        chapters = [chapter.strip() for chapter in session.mock_test_chapters if chapter.strip()]
        if not chapters:
            chapters = [session.current_topic or "JEE Main Mathematics"]

        context_blocks: list[str] = []
        for chapter in chapters:
            chapter_context = get_context(chapter, exam_type="jee")
            if chapter_context:
                context_blocks.append(f"### Chapter: {chapter}\n{chapter_context[:1400]}")

        combined_context = "\n\n".join(context_blocks).strip()
        if not combined_context:
            combined_context = "No external PYQ context found. Generate a valid JEE-level MCQ from the listed chapters."

        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Current exam status: {session.exam_status}\n"
            f"warnings_issued: {session.warnings_issued}\n"
            f"Allowed chapters for this mock test: {', '.join(chapters)}\n"
            "Rotate chapter coverage across the test and keep difficulty JEE Main appropriate.\n\n"
            "Use the following multi-chapter PYQ context:\n"
            f"{combined_context[:4200]}\n\n"
            "Return JSON only with keys:\n"
            '- "display_text": string (question + options A/B/C/D only, no answer)\n'
            '- "correct_option": one of A, B, C, D\n'
            '- "chapter": one of the allowed chapters\n'
        )
        raw = await asyncio.to_thread(generate_response, prompt)
        payload = self._load_json(raw)
        command = str(payload.get("action", "")).strip().lower()
        command_reason = str(payload.get("reason", "")).strip()

        if command == "terminate_exam":
            return self._terminate_exam(session, command_reason or "Maximum warnings exceeded.")
        if command == "issue_warning":
            session.warnings_issued += 1
            if session.warnings_issued >= self.WARNING_LIMIT:
                return self._terminate_exam(session, "Maximum warnings exceeded.")
            warning_reason = command_reason or "Suspicious activity detected in the video feed."
            return {
                "spoken_response": (
                    f"Warning {session.warnings_issued}/{self.WARNING_LIMIT}: {warning_reason}. "
                    "Stay in frame and focus on the exam."
                ),
                "whiteboard_actions": [
                    {
                        "action": "issue_warning",
                        "reason": warning_reason,
                        "warnings": session.warnings_issued,
                    }
                ],
                **self._metrics(session),
            }

        display_text = str(payload.get("display_text", "")).strip()
        correct_option = self._extract_option(str(payload.get("correct_option", "")))
        chapter = str(payload.get("chapter", "")).strip()

        if chapter not in chapters:
            chapter = chapters[session.questions_asked % len(chapters)]

        if not display_text or correct_option is None:
            display_text = (
                "Q. If roots of x^2 - 7x + 10 = 0 are alpha and beta, find alpha + beta.\n"
                "A) 5\nB) 7\nC) 10\nD) -7"
            )
            correct_option = "B"
            chapter = chapters[0]

        session.current_problem = {
            "prompt": display_text,
            "correct_option": correct_option,
            "chapter": chapter,
        }
        session.current_topic = chapter
        session.exam_status = "running"
        session.questions_asked += 1

        return {
            "spoken_response": display_text,
            "whiteboard_actions": [
                {
                    "action": "draw_text",
                    "content": f"[{chapter}] {display_text}",
                }
            ],
            **self._metrics(session),
        }

    async def _evaluate_and_advance(self, session: StudentSession, answer: str) -> dict[str, Any]:
        correct_option = self._extract_option(str(session.current_problem.get("correct_option", "")))
        is_correct = bool(correct_option and answer == correct_option)

        if is_correct:
            session.correct_attempts += 1
            session.mock_test_score += 4
            verdict = "Correct. +4"
        else:
            session.wrong_attempts += 1
            session.mock_test_score -= 1
            verdict = "Wrong. -1"

        next_question_payload = await self._generate_next_question(session)
        spoken_response = (
            f"{verdict} Score: {session.mock_test_score}\n\n"
            f"{next_question_payload['spoken_response']}"
        )

        next_question_payload["spoken_response"] = spoken_response
        score_action = {
            "action": "update_score",
            "score": session.mock_test_score,
            "correct": session.correct_attempts,
            "wrong": session.wrong_attempts,
        }
        next_question_payload["whiteboard_actions"] = [
            score_action,
            *(next_question_payload.get("whiteboard_actions") or []),
        ]
        next_question_payload["correct"] = is_correct
        next_question_payload["selected_option"] = answer
        next_question_payload["expected_option"] = correct_option
        return next_question_payload

    async def _evaluate_proctor_signal(self, session: StudentSession, user_message: str) -> dict[str, str]:
        if session.warnings_issued >= self.WARNING_LIMIT:
            return {"action": "terminate_exam", "reason": "Maximum warnings exceeded."}

        if not user_message:
            return {"action": "none", "reason": ""}

        if not self._message_contains_proctor_cues(user_message):
            return {"action": "none", "reason": ""}

        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            "You are deciding only the proctor command for this turn.\n"
            f"Current exam_status: {session.exam_status}\n"
            f"Current warnings_issued: {session.warnings_issued}\n"
            f"Latest student activity note: {user_message}\n\n"
            "Return JSON only with keys:\n"
            '- "action": one of "none", "identity_verified", "issue_warning", "terminate_exam"\n'
            '- "reason": short reason string (empty for "none")\n'
        )

        raw = await asyncio.to_thread(generate_response, prompt)
        payload = self._load_json(raw)
        action = str(payload.get("action", "none")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        if action not in {"none", "identity_verified", "issue_warning", "terminate_exam"}:
            action = "none"
            reason = ""
        return {"action": action, "reason": reason}

    def _message_contains_proctor_cues(self, message: str) -> bool:
        normalized = message.lower()
        proctor_keywords = (
            "camera",
            "face",
            "frame",
            "identity",
            "off-screen",
            "off screen",
            "phone",
            "mobile",
            "second person",
            "left the frame",
            "not visible",
            "video",
        )
        return any(keyword in normalized for keyword in proctor_keywords)

    def _looks_like_identity_confirmation(self, message: str) -> bool:
        normalized = message.lower()
        identity_keywords = (
            "face visible",
            "identity verified",
            "camera ready",
            "student visible",
            "video ready",
        )
        return any(keyword in normalized for keyword in identity_keywords)

    def _terminate_exam(self, session: StudentSession, reason: str) -> dict[str, Any]:
        session.exam_status = "terminated"
        session.current_problem = {}
        final_reason = reason or "Maximum warnings exceeded."
        return {
            "spoken_response": f"Exam terminated. {final_reason}",
            "whiteboard_actions": [
                {
                    "action": "terminate_exam",
                    "reason": final_reason,
                }
            ],
            **self._metrics(session),
        }

    def _metrics(self, session: StudentSession) -> dict[str, Any]:
        return {
            "mock_test_score": session.mock_test_score,
            "correct_attempts": session.correct_attempts,
            "wrong_attempts": session.wrong_attempts,
            "questions_asked": session.questions_asked,
            "warnings_issued": session.warnings_issued,
            "exam_status": session.exam_status,
        }

    def _load_json(self, raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            payload = json.loads(text)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return {}
            try:
                payload = json.loads(match.group(0))
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                return {}

    def _extract_option(self, text: str) -> str | None:
        match = re.search(r"\b([ABCD])\b", (text or "").upper())
        return match.group(1) if match else None
