from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from app.core.firestore_client import get_firestore_client
from app.services.knowledge_factory.chapter_models import ChapterKnowledge
from app.services.knowledge_factory.syllabus_models import (
    Syllabus,
    SyllabusChapter,
    SyllabusTopic,
)


@dataclass(frozen=True)
class CurriculumSectionRecord:
    section_id: str
    title: str
    number: str = ""
    concept_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CurriculumConceptRecord:
    concept_id: str
    title: str
    section_id: str = ""
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CurriculumChapterRecord:
    curriculum_id: str
    chapter_id: str
    title: str
    order: int
    slug: str = ""
    sections: list[CurriculumSectionRecord] = field(default_factory=list)
    concepts: list[CurriculumConceptRecord] = field(default_factory=list)


class SyllabusCurriculumLinker:
    """
    Links parsed syllabus topics to canonical curriculum knowledge.

    The linker is deterministic and Firestore-backed. It does not parse source
    documents and it does not store local state.
    """

    _MIN_CHAPTER_SCORE = 0.25
    _MIN_SECTION_SCORE = 0.45
    _MIN_CONCEPT_SCORE = 0.45
    _MAX_SECTION_LINKS = 8
    _MAX_CONCEPT_LINKS = 12

    _STOPWORDS = {
        "a",
        "an",
        "and",
        "as",
        "by",
        "chapter",
        "for",
        "from",
        "in",
        "main",
        "of",
        "on",
        "or",
        "the",
        "to",
        "unit",
        "with",
    }

    _IRREGULAR_TOKENS = {
        "matrices": "matrix",
        "vertices": "vertex",
        "indices": "index",
        "formulae": "formula",
    }

    def __init__(self, db: Any | None = None) -> None:
        self.db = db or get_firestore_client()

    def link_syllabus(
        self,
        syllabus: Syllabus,
    ) -> Syllabus:
        curriculum_chapters = self._load_curriculum_chapters_for_syllabus(
            syllabus
        )

        if not curriculum_chapters:
            return syllabus

        for syllabus_chapter in syllabus.chapters:
            for topic in syllabus_chapter.topics:
                matched_chapter = self._best_chapter_match(
                    syllabus_chapter,
                    topic,
                    curriculum_chapters,
                )

                self._apply_topic_links(
                    topic,
                    matched_chapter,
                )

        return syllabus

    def link_chapter(
        self,
        chapter: ChapterKnowledge,
    ) -> int:
        curriculum_chapter = self._chapter_record_from_chapter(
            chapter
        )
        updated_topic_count = 0

        for grade_ref in self._syllabus_grade_refs_for_chapter(chapter):
            for syllabus_chapter_snapshot in grade_ref.collection("chapters").stream():
                syllabus_chapter_data = syllabus_chapter_snapshot.to_dict() or {}
                syllabus_chapter = SyllabusChapter(
                    chapter_id=str(
                        syllabus_chapter_data.get("chapter_id")
                        or syllabus_chapter_snapshot.id
                    ),
                    order=self._int_value(
                        syllabus_chapter_data.get("order")
                    ),
                    title=str(
                        syllabus_chapter_data.get("title") or ""
                    ),
                )

                topics_ref = syllabus_chapter_snapshot.reference.collection(
                    "topics"
                )
                for topic_snapshot in topics_ref.stream():
                    topic_data = topic_snapshot.to_dict() or {}
                    topic = self._topic_from_firestore(
                        topic_snapshot.id,
                        topic_data,
                    )
                    score = self._chapter_match_score(
                        syllabus_chapter,
                        topic,
                        curriculum_chapter,
                    )

                    if score < self._MIN_CHAPTER_SCORE:
                        continue

                    payload = self._topic_link_payload(
                        topic,
                        curriculum_chapter,
                    )

                    if not self._has_links(payload):
                        continue

                    topic_snapshot.reference.set(
                        payload,
                        merge=True,
                    )
                    updated_topic_count += 1

        return updated_topic_count

    def _apply_topic_links(
        self,
        topic: SyllabusTopic,
        curriculum_chapter: CurriculumChapterRecord | None,
    ) -> None:

        if curriculum_chapter is None:

            topic.curriculum_id = ""

            topic.curriculum_chapter_id = ""

            topic.curriculum_section_ids = []

            topic.curriculum_concept_ids = []

            topic.link_confidence = 0.0

            topic.link_method = "unmatched"

            print(
                f"[KnowledgeLinker] No curriculum match: {topic.title}"
            )

            return

        payload = self._topic_link_payload(
            topic,
            curriculum_chapter,
        )

        topic.curriculum_id = payload["curriculum_id"]

        topic.curriculum_chapter_id = payload["curriculum_chapter_id"]

        topic.curriculum_section_ids = list(
            payload["curriculum_section_ids"]
        )

        topic.curriculum_concept_ids = list(
            payload["curriculum_concept_ids"]
        )

        topic.link_confidence = payload["link_confidence"]

        topic.link_method = payload["link_method"]
    
    def _topic_link_payload(
        self,
        topic: SyllabusTopic,
        curriculum_chapter: CurriculumChapterRecord,
    ) -> dict[str, Any]:
        section_ids = self._matching_section_ids(
            topic,
            curriculum_chapter,
        )
        concept_ids = self._matching_concept_ids(
            topic,
            curriculum_chapter,
            section_ids,
        )

        return {
            "curriculum_id": curriculum_chapter.curriculum_id,
            "curriculum_chapter_id": curriculum_chapter.chapter_id,
            "curriculum_section_ids": section_ids,
            "curriculum_concept_ids": concept_ids,
            "link_confidence": 1.0,
            "link_method": "automatic",
        }

    def _has_links(
        self,
        payload: dict[str, Any],
    ) -> bool:
        return bool(
            payload.get("curriculum_chapter_id")
            or payload.get("curriculum_section_ids")
            or payload.get("curriculum_concept_ids")
        )

    def _best_chapter_match(
        self,
        syllabus_chapter: SyllabusChapter,
        topic: SyllabusTopic,
        curriculum_chapters: list[CurriculumChapterRecord],
    ) -> CurriculumChapterRecord | None:
        best_chapter: CurriculumChapterRecord | None = None
        best_score = 0.0

        for curriculum_chapter in curriculum_chapters:
            score = self._chapter_match_score(
                syllabus_chapter,
                topic,
                curriculum_chapter,
            )
            if score > best_score:
                best_chapter = curriculum_chapter
                best_score = score

        if best_score < self._MIN_CHAPTER_SCORE:
            return None

        return best_chapter

    def _chapter_match_score(
        self,
        syllabus_chapter: SyllabusChapter,
        topic: SyllabusTopic,
        curriculum_chapter: CurriculumChapterRecord,
    ) -> float:
        topic_score = self._coverage_score(
            self._topic_text(topic),
            self._chapter_text(curriculum_chapter),
        )
        chapter_score = self._coverage_score(
            syllabus_chapter.title,
            self._chapter_text(curriculum_chapter),
        )
        score = max(
            topic_score,
            chapter_score * 0.9,
        )

        if self._same_order(
            syllabus_chapter.order,
            curriculum_chapter.order,
        ) and score > 0:
            score += 0.2

        if self._same_chapter_id(
            syllabus_chapter.chapter_id,
            curriculum_chapter.chapter_id,
        ):
            score += 0.2

        return min(
            score,
            1.0,
        )

    def _matching_section_ids(
        self,
        topic: SyllabusTopic,
        chapter: CurriculumChapterRecord,
    ) -> list[str]:
        scored_sections: list[tuple[float, str]] = []
        topic_text = self._topic_text(topic)

        for section in chapter.sections:

            section_text = " ".join(
                [
                    section.title,
                    section.number,
                    section.section_id,
                ]
            )

            score = max(

                self._coverage_score(
                    topic.title,
                    section_text,
                ),

                self._coverage_score(
                    topic_text,
                    section_text,
                ),
            )

            #
            # Bonus score if topic title
            # directly contains section title.
            #

            if (
                section.title.lower()
                in topic.title.lower()
            ):
                score += 0.25

            #
            # Bonus if section number
            # appears in topic.
            #

            if (
                section.number
                and section.number
                in topic_text
            ):
                score += 0.15

            score = min(
                score,
                1.0,
            )

            print(
                f"[SECTION] "
                f"{topic.title}"
                f" -> "
                f"{section.section_id}"
                f" score={score:.2f}"
            )

            if score < self._MIN_SECTION_SCORE:
                continue

            scored_sections.append(
                (
                    score,
                    section.section_id,
                )
            )
        return self._ordered_unique(
            section_id
            for _, section_id in sorted(
                scored_sections,
                key=lambda item: item[0],
                reverse=True,
            )
        )[: self._MAX_SECTION_LINKS]

    def _matching_concept_ids(
        self,
        topic: SyllabusTopic,
        chapter: CurriculumChapterRecord,
        section_ids: list[str],
    ) -> list[str]:
        scored_concepts: list[tuple[float, str]] = []
        topic_text = self._topic_text(topic)
        matched_sections = set(section_ids)

        for concept in chapter.concepts:
            concept_text = " ".join(
                [
                    concept.title,
                    *concept.aliases,
                    *concept.keywords,
                ]
            )
            score = max(
                self._coverage_score(topic.title, concept_text),
                self._coverage_score(topic_text, concept_text),
            )

            if concept.section_id in matched_sections:
                score = max(score, self._MIN_CONCEPT_SCORE)

            if score < self._MIN_CONCEPT_SCORE:
                continue

            scored_concepts.append(
                (score, concept.concept_id)
            )

        return self._ordered_unique(
            concept_id
            for _, concept_id in sorted(
                scored_concepts,
                key=lambda item: item[0],
                reverse=True,
            )
        )[: self._MAX_CONCEPT_LINKS]

    def _load_curriculum_chapters_for_syllabus(
        self,
        syllabus: Syllabus,
    ) -> list[CurriculumChapterRecord]:
        curriculum_chapters: list[CurriculumChapterRecord] = []

        for curriculum_id in self._candidate_curriculum_ids(syllabus):
            chapter_ref = (
                self.db.collection("curriculums")
                .document(curriculum_id)
                .collection("chapters")
            )
            chapter_snapshots = list(chapter_ref.stream())

            if not chapter_snapshots:
                continue

            for chapter_snapshot in chapter_snapshots:
                curriculum_chapters.append(
                    self._chapter_record_from_snapshot(
                        curriculum_id,
                        chapter_snapshot,
                    )
                )

            if curriculum_chapters:
                return curriculum_chapters

        return curriculum_chapters

    def _candidate_curriculum_ids(
        self,
        syllabus: Syllabus,
    ) -> list[str]:
        board = self._slug(syllabus.board)
        grade = self._slug(syllabus.grade)
        version = self._slug(syllabus.version)
        subject = self._slug(syllabus.subject)

        candidates = [
            "-".join(
                item
                for item in (grade, version, subject)
                if item and item != "unknown"
            ),
            "-".join(
                item
                for item in (board, grade, version, subject)
                if item and item != "unknown"
            ),
            "_".join(
                item
                for item in (board, grade, subject)
                if item and item != "unknown"
            ),
            "_".join(
                item
                for item in (board, self._numeric_grade(grade))
                if item
            ),
            "-".join(
                item
                for item in (board, grade, subject)
                if item and item != "unknown"
            ),
            syllabus.syllabus_id,
        ]

        return self._ordered_unique(
            candidate
            for candidate in candidates
            if candidate
        )

    def _chapter_record_from_snapshot(
        self,
        curriculum_id: str,
        chapter_snapshot: Any,
    ) -> CurriculumChapterRecord:
        data = chapter_snapshot.to_dict() or {}
        chapter_id = str(
            data.get("chapter_id") or chapter_snapshot.id
        )

        return CurriculumChapterRecord(
            curriculum_id=curriculum_id,
            chapter_id=chapter_id,
            title=str(data.get("title") or data.get("name") or ""),
            order=self._int_value(data.get("order"))
            or self._order_from_chapter_id(chapter_id),
            slug=str(data.get("slug") or ""),
            sections=self._section_records_from_ref(
                chapter_snapshot.reference
            ),
            concepts=self._concept_records_from_ref(
                chapter_snapshot.reference
            ),
        )

    def _chapter_record_from_chapter(
        self,
        chapter: ChapterKnowledge,
    ) -> CurriculumChapterRecord:
        return CurriculumChapterRecord(
            curriculum_id=chapter.metadata.curriculum_id,
            chapter_id=chapter.metadata.chapter_id,
            title=chapter.metadata.title,
            order=chapter.metadata.order,
            slug=chapter.metadata.slug,
            sections=[
                CurriculumSectionRecord(
                    section_id=section.section_id,
                    title=section.title,
                    number=section.number,
                    concept_ids=list(
                        getattr(section, "concept_ids", [])
                    ),
                )
                for section in chapter.sections
            ],
            concepts=[
                CurriculumConceptRecord(
                    concept_id=concept.concept_id,
                    title=concept.title,
                    section_id=concept.section_id,
                    aliases=list(concept.aliases),
                    keywords=list(concept.keywords),
                )
                for concept in chapter.concepts
            ],
        )

    def _section_records_from_ref(
        self,
        chapter_ref: Any,
    ) -> list[CurriculumSectionRecord]:
        records: list[CurriculumSectionRecord] = []

        for section_snapshot in chapter_ref.collection("sections").stream():
            data = section_snapshot.to_dict() or {}
            section_id = str(
                data.get("section_id") or section_snapshot.id
            )
            records.append(
                CurriculumSectionRecord(
                    section_id=section_id,
                    title=str(data.get("title") or ""),
                    number=str(data.get("number") or ""),
                    concept_ids=self._string_list(
                        data.get("concept_ids")
                    ),
                )
            )

        return records

    def _concept_records_from_ref(
        self,
        chapter_ref: Any,
    ) -> list[CurriculumConceptRecord]:
        records: list[CurriculumConceptRecord] = []

        for concept_snapshot in chapter_ref.collection("concepts").stream():
            data = concept_snapshot.to_dict() or {}
            concept_id = str(
                data.get("concept_id") or concept_snapshot.id
            )
            records.append(
                CurriculumConceptRecord(
                    concept_id=concept_id,
                    title=str(data.get("title") or ""),
                    section_id=str(data.get("section_id") or ""),
                    aliases=self._string_list(data.get("aliases")),
                    keywords=self._string_list(data.get("keywords")),
                )
            )

        return records

    def _syllabus_grade_refs_for_chapter(
        self,
        chapter: ChapterKnowledge,
    ) -> list[Any]:
        board, grade = self._syllabus_key_from_chapter(chapter)

        if not board or not grade:
            return []

        return [
            self.db.collection("syllabuses")
            .document(board)
            .collection("grades")
            .document(grade)
        ]

    def _syllabus_key_from_chapter(
        self,
        chapter: ChapterKnowledge,
    ) -> tuple[str, str]:
        curriculum_id = self._slug(chapter.metadata.curriculum_id)
        exam = self._slug(chapter.metadata.exam)

        if "jee-advanced" in curriculum_id or "jee-advanced" in exam:
            return "jee", "jee-advanced"

        if "jee-main" in curriculum_id or "jee-main" in exam or exam == "jee":
            return "jee", "jee-main"

        if "cbse" in curriculum_id or "cbse" in exam:
            grade = self._normalize_grade(chapter.metadata.grade)
            return "cbse", grade

        return "", ""

    def _topic_from_firestore(
        self,
        topic_id: str,
        data: dict[str, Any],
    ) -> SyllabusTopic:
        return SyllabusTopic(
            topic_id=str(data.get("topic_id") or topic_id),
            order=self._int_value(data.get("order")),
            title=str(data.get("title") or ""),
            subtopics=self._string_list(data.get("subtopics")),
        )

    def _topic_text(
        self,
        topic: SyllabusTopic,
    ) -> str:
        return " ".join(
            [
                topic.title,
                *topic.subtopics,
            ]
        )

    def _chapter_text(
        self,
        chapter: CurriculumChapterRecord,
    ) -> str:
        return " ".join(
            [
                chapter.title,
                chapter.slug,
                chapter.chapter_id,
            ]
        )

    def _coverage_score(
        self,
        query: str,
        candidate: str,
    ) -> float:
        query_tokens = self._tokens(query)
        candidate_tokens = self._tokens(candidate)

        if not query_tokens or not candidate_tokens:
            return 0.0

        return len(query_tokens & candidate_tokens) / len(query_tokens)

    def _tokens(
        self,
        text: str,
    ) -> set[str]:
        tokens: set[str] = set()

        for raw_token in re.findall(r"[a-z0-9]+", str(text or "").lower()):
            normalized = self._normalize_token(raw_token)
            if not normalized or normalized in self._STOPWORDS:
                continue
            tokens.add(normalized)

        return tokens

    def _normalize_token(
        self,
        token: str,
    ) -> str:
        token = token.strip().lower()

        if token in self._IRREGULAR_TOKENS:
            return self._IRREGULAR_TOKENS[token]

        if token.endswith("ies") and len(token) > 4:
            return token[:-3] + "y"

        if token.endswith("s") and len(token) > 3:
            return token[:-1]

        return token

    def _same_order(
        self,
        left: int,
        right: int,
    ) -> bool:
        return bool(left and right and left == right)

    def _same_chapter_id(
        self,
        left: str,
        right: str,
    ) -> bool:
        return (
            self._order_from_chapter_id(left) != 0
            and self._order_from_chapter_id(left) == self._order_from_chapter_id(right)
        )

    def _order_from_chapter_id(
        self,
        chapter_id: str,
    ) -> int:
        match = re.search(r"(\d+)$", str(chapter_id or ""))
        if not match:
            return 0
        return int(match.group(1))

    def _normalize_grade(
        self,
        grade: str,
    ) -> str:
        slug = self._slug(grade)

        if slug in {"jee-main", "jee-advanced"}:
            return slug

        match = re.search(r"(\d{1,2})", slug)
        if not match:
            return slug

        return f"grade-{int(match.group(1)):02d}"

    def _numeric_grade(
        self,
        grade: str,
    ) -> str:
        match = re.search(r"(\d{1,2})", str(grade or ""))
        if not match:
            return ""

        return str(int(match.group(1)))

    def _string_list(
        self,
        value: Any,
    ) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    def _int_value(
        self,
        value: Any,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _ordered_unique(
        self,
        values,
    ) -> list[str]:
        seen: set[str] = set()
        unique_values: list[str] = []

        for value in values:
            normalized = str(value or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(normalized)

        return unique_values

    def _slug(
        self,
        value: str,
    ) -> str:
        slug = str(value or "").lower()
        slug = slug.replace("&", "and")
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")
