from __future__ import annotations

import logging
from typing import List, Optional
import logging

from app.core import config
from app.core.firestore_client import get_knowledge_factory_firestore_client
from app.services.knowledge_factory.knowledge_factory_client import (
    KnowledgeFactoryClient,
)


_CURRICULUM_CACHE: dict[tuple[int, str], dict] = {}
logger = logging.getLogger("mathverse.knowledge_factory")
logger = logging.getLogger("mathverse.knowledge_factory")


def _normalise(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _package_to_curriculum(package_id: str, package: dict) -> dict:
    concepts = package.get("concepts") or []
    chapters = []
    for chapter in package.get("chapters") or []:
        if not isinstance(chapter, dict):
            continue
        chapter_number = chapter.get("number")
        chapter_id = str(chapter.get("id") or chapter_number or "").strip()
        chapter_title = str(chapter.get("title") or "").strip()
        chapter_concepts = [
            item
            for item in concepts
            if isinstance(item, dict)
            and (
                not chapter_number
                or _normalise(item.get("section_number")).startswith(
                    _normalise(chapter_number)
                )
            )
        ]
        chapters.append(
            {
                "id": chapter_id,
                "slug": _normalise(chapter_title).replace(" ", "_"),
                "number": chapter_number,
                "title": chapter_title,
                "summary": "",
                "concepts": chapter_concepts,
                "knowledge_package_document_id": package_id,
            }
        )

    return {
        "document_id": package_id,
        "schema_version": package.get("schema_version"),
        "metadata": package.get("metadata") or {},
        "chapters": chapters,
        "knowledge_package": package,
    }


def get_grade_curriculum(grade: int, exam: str = "cbse") -> dict:
    """Fetch curriculum only from the configured Knowledge Factory package."""
    cache_key = (int(grade or 10), str(exam or "cbse").lower())
    cached = _CURRICULUM_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        client = KnowledgeFactoryClient.from_config(
            firestore_client=get_knowledge_factory_firestore_client()
        )
        packages = client.list_packages()
        if config.APP_ENV.lower() in {"development", "dev", "test"}:
            logger.info(
                "Knowledge Factory lookup subject=Mathematics grade=%s board=%s chapter=<curriculum> document_id=%s source=firestore",
                grade,
                exam,
                config.KNOWLEDGE_FACTORY_DOCUMENT_ID or "<metadata-resolution>",
            )
    except Exception as error:
        raise RuntimeError(
            "Knowledge Factory Firestore could not be read; "
            "MathVerse has no local knowledge fallback."
        ) from error
    selected: tuple[str, dict] | None = None
    for package_id, package in packages:
        if config.KNOWLEDGE_FACTORY_DOCUMENT_ID and package_id == config.KNOWLEDGE_FACTORY_DOCUMENT_ID:
            selected = (package_id, package)
            break
        metadata = package.get("metadata") if isinstance(package, dict) else None
        if not isinstance(metadata, dict):
            continue
        if (
            _normalise(metadata.get("subject")) == _normalise("Mathematics")
            and _normalise(metadata.get("grade")) in {_normalise(grade), _normalise(f"Grade {grade}")}
            and _normalise(metadata.get("board")) in {_normalise(exam), _normalise("CBSE")}
        ):
            selected = (package_id, package)
            break

    if selected is None:
        raise LookupError(
            f"No Knowledge Factory package resolved for subject=Mathematics "
            f"grade={grade} board={exam}. Configure metadata or "
            "KNOWLEDGE_FACTORY_DOCUMENT_ID; no local fallback is available."
        )

    if config.APP_ENV.lower() in {"development", "dev", "test"}:
        logger.info(
            "Knowledge Factory resolution subject=%s grade=%s board=%s chapter=%s document_id=%s source=firestore",
            "Mathematics",
            grade,
            exam,
            "<all-chapters>",
            selected[0],
        )
        print(
            "[mathverse] Knowledge Factory resolution: "
            f"subject=Mathematics grade={grade} board={exam} "
            f"chapter=<all-chapters> document_id={selected[0]} source=firestore"
        )

    payload = _package_to_curriculum(*selected)
    if config.APP_ENV.lower() in {"development", "dev", "test"}:
        logger.info(
            "Knowledge Factory resolved subject=Mathematics grade=%s board=%s chapter=<package> document_id=%s source=firestore",
            grade,
            exam,
            selected[0],
        )
    _CURRICULUM_CACHE[cache_key] = payload
    return payload


def list_chapters(grade: int, exam: str = "cbse") -> List[dict]:
    return get_grade_curriculum(grade, exam).get("chapters", [])


def get_default_topic_slug(grade: int, exam: str = "cbse") -> str:
    return get_grade_curriculum(grade, exam).get("default_topic_slug", "")


def get_topic(grade: int, topic_slug: Optional[str] = None, exam: str = "cbse") -> Optional[dict]:
    slug = topic_slug or get_default_topic_slug(grade, exam)
    for chapter in list_chapters(grade, exam):
        if chapter.get("slug") == slug:
            return chapter
    return None


def _normalize_match_text(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").lower().split())


def _topic_match_terms(chapter: dict) -> list[str]:
    terms = [
        chapter.get("slug"),
        chapter.get("title"),
        chapter.get("chapter"),
        chapter.get("name"),
        chapter.get("summary"),
    ]
    terms.extend(chapter.get("book_topics") or [])
    for concept in chapter.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        terms.extend(
            [
                concept.get("id"),
                concept.get("title"),
                concept.get("definition"),
            ]
        )
    return [_normalize_match_text(term) for term in terms if str(term or "").strip()]


def find_topic_by_message(grade: int, message: str, exam: str = "cbse") -> Optional[dict]:
    """Return the best matching chapter/topic for free-form student text."""
    normalized_message = _normalize_match_text(message)
    if not normalized_message:
        return None

    chapters = list_chapters(grade, exam)
    best_score = 0
    best_topic: Optional[dict] = None

    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue

        score = 0
        for term in _topic_match_terms(chapter):
            if not term:
                continue
            if normalized_message == term:
                score = max(score, 100)
            elif term in normalized_message:
                score = max(score, 80 if len(term) >= 5 else 20)
            elif normalized_message in term:
                score = max(score, 60 if len(normalized_message) >= 5 else 10)

        if score > best_score:
            best_score = score
            best_topic = chapter

    return best_topic if best_score >= 20 else None


def get_chapter_position(grade: int, topic_slug: Optional[str] = None, exam: str = "cbse") -> tuple[int, int]:
    chapters = list_chapters(grade, exam)
    total = len(chapters) or 1
    if not topic_slug:
        return 1, total
    for index, chapter in enumerate(chapters, start=1):
        if chapter.get("slug") == topic_slug:
            return index, total
    return 1, total


def get_next_topic(grade: int, topic_slug: Optional[str] = None, exam: str = "cbse") -> Optional[dict]:
    chapters = list_chapters(grade, exam)
    if not chapters:
        return None

    if not topic_slug:
        return chapters[0]

    for index, chapter in enumerate(chapters):
        if chapter.get("slug") == topic_slug:
            next_index = index + 1
            return chapters[next_index] if next_index < len(chapters) else None

    return chapters[0]


def get_topic_concepts(grade: int, topic_slug: str, exam: str = "cbse") -> List[dict]:
    topic = get_topic(grade, topic_slug, exam)
    return topic.get("concepts", []) if topic else []


def get_concept(grade: int, topic_slug: str, concept_id: Optional[str] = None, exam: str = "cbse") -> Optional[dict]:
    concepts = get_topic_concepts(grade, topic_slug, exam)
    if not concepts:
        return None
    if concept_id is None:
        return concepts[0]
    for concept in concepts:
        if concept.get("id") == concept_id:
            return concept
    return None


def get_next_concept(
    grade: int,
    topic_slug: str,
    concept_id: Optional[str] = None,
    exam: str = "cbse",
) -> Optional[dict]:
    concepts = get_topic_concepts(grade, topic_slug, exam)
    if not concepts:
        return None
    if not concept_id:
        return concepts[0]
    for index, concept in enumerate(concepts):
        if concept.get("id") == concept_id:
            next_index = index + 1
            return concepts[next_index] if next_index < len(concepts) else None
    return concepts[0]
