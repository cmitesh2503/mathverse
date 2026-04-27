from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

from ..models.session import TutorSessionRecord, utc_now
from ..tutor_brain.curriculum import get_default_topic_slug, get_topic


STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "chapter_tests.json"


class ChapterTestAgent:
    def __init__(self, store_path: Path = STORE_PATH) -> None:
        self.store_path = store_path
        self._lock = Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def get_or_create(self, session: TutorSessionRecord, refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            store = self._load_store()
            if not refresh and session.session_id in store["tests"]:
                record = store["tests"][session.session_id]
                return {
                    "chapter_test": record["public"],
                    "latest_result": record.get("latest_result"),
                }

            generated = self._generate_test(session)
            store["tests"][session.session_id] = generated
            self._save_store(store)
            return {
                "chapter_test": generated["public"],
                "latest_result": generated.get("latest_result"),
            }

    def evaluate(self, session_id: str, answers: dict[str, str]) -> dict[str, Any]:
        with self._lock:
            store = self._load_store()
            record = store["tests"].get(session_id)
            if not record:
                raise KeyError(session_id)

            total = 0.0
            max_score = 0.0
            feedback: list[dict[str, Any]] = []

            for question in record["public"]["questions"]:
                grading = record["grading"][question["id"]]
                submitted = str(answers.get(question["id"], "")).strip()
                max_score += 1.0

                if grading["mode"] == "keywords":
                    score, correct, note = self._grade_keywords(submitted, grading["keywords"])
                else:
                    score, correct, note = self._grade_problem(submitted, grading)

                total += score
                feedback.append(
                    {
                        "question_id": question["id"],
                        "prompt": question["prompt"],
                        "correct": correct,
                        "score": round(score, 2),
                        "max_score": 1.0,
                        "submitted": submitted,
                        "expected": grading["expected_text"],
                        "feedback": note,
                    }
                )

            percentage = round((total / max_score) * 100) if max_score else 0
            result = {
                "test_id": record["public"]["test_id"],
                "score": round(total, 2),
                "max_score": round(max_score, 2),
                "percentage": percentage,
                "verdict": self._verdict(percentage),
                "submitted_at": utc_now().isoformat(),
                "feedback": feedback,
            }
            record["latest_result"] = result
            self._save_store(store)
            return result

    def _generate_test(self, session: TutorSessionRecord) -> dict[str, Any]:
        topic_slug = session.topic_slug or get_default_topic_slug(session.grade)
        topic = get_topic(session.grade, topic_slug) or {}
        topic_title = topic.get("title") or session.topic_title or "Mathematics"
        chapter_label = (
            session.metadata.get("chapter_label")
            if isinstance(session.metadata.get("chapter_label"), str)
            else f"Class {session.grade} - {topic_title}"
        )
        concepts = [concept for concept in topic.get("concepts", []) if isinstance(concept, dict)]

        questions: list[dict[str, Any]] = []
        grading: dict[str, dict[str, Any]] = {}
        seen_prompts: set[str] = set()

        if concepts and concepts[0].get("definition"):
            concept = concepts[0]
            question_id = "recall-1"
            definition = str(concept["definition"]).strip()
            questions.append(
                {
                    "id": question_id,
                    "prompt": f"In one or two lines, explain {concept['title']}.",
                    "concept_title": concept["title"],
                    "kind": "short",
                    "answer_format": "Short explanation",
                }
            )
            grading[question_id] = {
                "mode": "keywords",
                "keywords": self._keywords(f"{concept['title']} {definition}"),
                "expected_text": definition,
            }

        counter = 1
        for concept in concepts:
            for bucket in ("exercise_problems", "practice_problems", "ncert_examples"):
                for problem in concept.get(bucket, []):
                    prompt = str(problem.get("prompt", "")).strip()
                    if not prompt or prompt in seen_prompts:
                        continue
                    seen_prompts.add(prompt)
                    question_id = f"problem-{counter}"
                    counter += 1
                    answer_type = str(problem.get("answer_type", "text"))
                    questions.append(
                        {
                            "id": question_id,
                            "prompt": prompt,
                            "concept_title": concept.get("title"),
                            "kind": "pair" if answer_type == "pair" else "numeric" if answer_type == "number" else "short",
                            "answer_format": self._answer_format(answer_type),
                        }
                    )
                    grading[question_id] = {
                        "mode": "problem",
                        "answer_type": answer_type,
                        "expected": problem.get("answer"),
                        "accepted_answers": problem.get("accepted_answers", []),
                        "answer_labels": problem.get("answer_labels", []),
                        "expected_text": self._expected_text(problem),
                    }
                    if len(questions) >= 5:
                        break
                if len(questions) >= 5:
                    break
            if len(questions) >= 5:
                break

        if len(questions) < 5:
            for concept in concepts[1:]:
                board_work = concept.get("board_work", [])
                if not board_work:
                    continue
                question_id = f"concept-{len(questions) + 1}"
                anchor = str(board_work[0]).strip()
                questions.append(
                    {
                        "id": question_id,
                        "prompt": f"State the key board idea for {concept['title']}.",
                        "concept_title": concept.get("title"),
                        "kind": "short",
                        "answer_format": "Short explanation",
                    }
                )
                grading[question_id] = {
                    "mode": "keywords",
                    "keywords": self._keywords(f"{concept.get('title', '')} {anchor}"),
                    "expected_text": anchor,
                }
                if len(questions) >= 5:
                    break

        public = {
            "test_id": f"{session.session_id}-chapter-test",
            "title": f"{topic_title} Chapter Test",
            "chapter_label": chapter_label,
            "topic_title": topic_title,
            "instructions": "Answer each question carefully. Numeric or pair answers can be brief. Short answers can be one or two lines.",
            "generated_at": utc_now().isoformat(),
            "questions": questions[:5],
        }
        return {"public": public, "grading": grading, "latest_result": None}

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"tests": {}}
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"tests": {}}
        raw.setdefault("tests", {})
        return raw

    def _save_store(self, store: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")

    def _answer_format(self, answer_type: str) -> str:
        if answer_type == "pair":
            return "Write both values, for example q = 7, r = 2"
        if answer_type == "number":
            return "Numeric answer"
        return "Short answer"

    def _expected_text(self, problem: dict[str, Any]) -> str:
        answer_type = str(problem.get("answer_type", "text"))
        answer = problem.get("answer")
        if answer_type == "pair" and isinstance(answer, list) and len(answer) >= 2:
            labels = problem.get("answer_labels", ["x", "y"])
            first_label = labels[0] if len(labels) > 0 else "x"
            second_label = labels[1] if len(labels) > 1 else "y"
            return f"{first_label} = {answer[0]}, {second_label} = {answer[1]}"
        return str(answer)

    def _keywords(self, text: str) -> list[str]:
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "into",
            "there",
            "exist",
            "such",
            "than",
            "must",
            "always",
        }
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return [word for word in dict.fromkeys(words) if len(word) > 2 and word not in stopwords][:6]

    def _grade_problem(self, submitted: str, grading: dict[str, Any]) -> tuple[float, bool, str]:
        answer_type = grading["answer_type"]
        if answer_type == "number":
            values = re.findall(r"-?\d+(?:\.\d+)?", submitted)
            if not values:
                return 0.0, False, "A numeric answer was expected."
            correct = abs(float(values[0]) - float(grading["expected"])) < 1e-9
            return (1.0 if correct else 0.0), correct, "Correct numeric answer." if correct else "Check the arithmetic carefully."
        if answer_type == "pair":
            values = [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", submitted)]
            expected = [float(item) for item in grading["expected"]]
            if len(values) < 2:
                return 0.0, False, "Two values were expected."
            matches = sum(abs(a - b) < 1e-9 for a, b in zip(values[:2], expected[:2]))
            score = matches / 2
            return score, matches == 2, "Both values are correct." if matches == 2 else "One or both values need correction."
        normalized = re.sub(r"\s+", " ", submitted.strip().lower())
        accepted = [str(grading["expected"]).lower(), *[str(item).lower() for item in grading["accepted_answers"]]]
        correct = normalized in accepted
        return (1.0 if correct else 0.0), correct, "Correct answer." if correct else "Review the definition or concept wording."

    def _grade_keywords(self, submitted: str, keywords: list[str]) -> tuple[float, bool, str]:
        lowered = submitted.lower()
        matches = sum(keyword in lowered for keyword in keywords)
        ratio = matches / max(1, len(keywords))
        if ratio >= 0.6:
            return 1.0, True, "Good coverage of the key idea."
        if ratio >= 0.3:
            return 0.5, False, "Partially correct. Include the missing key terms."
        return 0.0, False, "The answer misses the key chapter terms."

    def _verdict(self, percentage: int) -> str:
        if percentage >= 85:
            return "Excellent"
        if percentage >= 60:
            return "Good progress"
        return "Needs revision"


chapter_test_agent = ChapterTestAgent()
