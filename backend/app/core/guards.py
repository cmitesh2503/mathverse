from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from .firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client


def get_db():
    return get_firestore_client()


def is_first_chapter_free(requested_grade: str | int | None, topic_slug: str | None = None, exam: str = "cbse") -> bool:
    try:
        from ..tutor_brain.curriculum import get_chapter_position, get_default_topic_slug

        grade = int(requested_grade or 10)
        resolved_topic_slug = topic_slug or get_default_topic_slug(grade, exam)
        chapter_index, _ = get_chapter_position(grade, resolved_topic_slug, exam)
        return chapter_index == 1
    except Exception as error:
        print(f"Free chapter check failed; requiring subscription ({type(error).__name__}: {error})")
        return False


def _normalize_grade(value: str | int | None) -> int:
    try:
        return int(value or 10)
    except (TypeError, ValueError):
        return 10


def _normalize_exam(value: str | None) -> str:
    return "jee" if str(value or "").strip().lower() == "jee" else "cbse"


def _chapter_agenda(chapter: dict[str, Any], *, fallback: str) -> list[str]:
    for key in ("agenda", "book_topics"):
        values = chapter.get(key) if isinstance(chapter, dict) else None
        if isinstance(values, list):
            agenda = [str(item).strip() for item in values if str(item).strip()]
            if agenda:
                return agenda

    concepts = chapter.get("concepts") if isinstance(chapter, dict) else None
    if isinstance(concepts, list):
        agenda = [
            str(item.get("title", "")).strip()
            for item in concepts
            if isinstance(item, dict) and str(item.get("title", "")).strip()
        ]
        if agenda:
            return agenda

    return [fallback] if fallback else []


def _normalize_match_text(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").lower().split())


def _chapter_index_for_slug(chapters: list[dict], topic_slug: str | None) -> int | None:
    if not topic_slug:
        return None
    for index, chapter in enumerate(chapters):
        if isinstance(chapter, dict) and chapter.get("slug") == topic_slug:
            return index
    return None


def _session_chapter_index(session: Any, chapters: list[dict], fallback_slug: str | None = None) -> int:
    fallback_index = _chapter_index_for_slug(chapters, fallback_slug)
    if fallback_index is not None:
        return fallback_index

    try:
        index = int(getattr(session, "current_chapter_index", 0) or 0)
    except (TypeError, ValueError):
        index = 0
    if 0 <= index < len(chapters):
        return index

    wanted = _normalize_match_text(
        getattr(session, "chapter_name", None)
        or getattr(session, "current_chapter", None)
        or getattr(session, "current_topic", None)
    )
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            continue
        candidates = [
            chapter.get("slug"),
            chapter.get("title"),
            chapter.get("chapter"),
            chapter.get("name"),
        ]
        if any(wanted and _normalize_match_text(candidate) == wanted for candidate in candidates):
            return index

    return 0


def resolve_tutor_action_access_topic(
    *,
    session: Any = None,
    action: str = "",
    requested_grade: str | int | None = None,
    topic_slug: str | None = None,
    exam: str = "cbse",
) -> str | None:
    normalized_action = str(action or "").strip().lower()
    topic_switch_actions = {"next_topic", "next_chapter", "skip_topic", "skip_chapter"}

    try:
        from ..tutor_brain.curriculum import list_chapters

        grade = _normalize_grade(requested_grade)
        normalized_exam = _normalize_exam(exam)
        chapters = [chapter for chapter in list_chapters(grade, normalized_exam) if isinstance(chapter, dict)]
    except Exception as error:
        print(f"Access target resolution failed; using requested topic ({type(error).__name__}: {error})")
        return topic_slug

    if not chapters:
        return topic_slug

    current_index = _session_chapter_index(session, chapters, fallback_slug=topic_slug)
    current_chapter = chapters[current_index]
    current_slug = str(current_chapter.get("slug") or topic_slug or "").strip() or None

    if normalized_action not in topic_switch_actions:
        return topic_slug or current_slug

    if normalized_action in {"next_chapter", "skip_chapter"}:
        next_index = current_index + 1
        if next_index < len(chapters):
            return str(chapters[next_index].get("slug") or "").strip() or current_slug
        return current_slug

    agenda = [str(item).strip() for item in (getattr(session, "agenda", []) or []) if str(item).strip()]
    if not agenda:
        title = str(current_chapter.get("title") or current_chapter.get("chapter") or current_slug or "").strip()
        agenda = _chapter_agenda(current_chapter, fallback=title)

    try:
        topic_index = int(getattr(session, "current_topic_index", 0) or 0)
    except (TypeError, ValueError):
        topic_index = 0

    if topic_index + 1 < len(agenda):
        return current_slug

    next_index = current_index + 1
    if next_index < len(chapters):
        return str(chapters[next_index].get("slug") or "").strip() or current_slug

    return current_slug


def verify_tutor_action_access(
    *,
    user_id: str | None,
    requested_grade: str | int | None,
    session: Any = None,
    action: str = "",
    topic_slug: str | None = None,
    exam: str = "cbse",
) -> bool:
    access_topic_slug = resolve_tutor_action_access_topic(
        session=session,
        action=action,
        requested_grade=requested_grade,
        topic_slug=topic_slug,
        exam=exam,
    )
    return verify_access_privileges(
        user_id=user_id,
        requested_grade=requested_grade,
        topic_slug=access_topic_slug,
        exam=exam,
    )


def verify_access_privileges(
    user_id: str | None,
    requested_grade: str | int | None,
    topic_slug: str | None = None,
    exam: str = "cbse",
) -> bool:
    """
    Validates subscription access privileges.
    Bypasses access restrictions automatically for accounts with an administrative role.
    """
    if is_first_chapter_free(requested_grade, topic_slug, exam):
        print(f"Free Chapter Access: Grade {requested_grade}, topic {topic_slug or 'default'}.")
        return True

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session payload missing user_id identifier."
        )

    db = get_db()
    try:
        user_doc = db.collection("users").document(user_id).get(timeout=FIRESTORE_TIMEOUT_SECONDS)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore unavailable during subscription check: {str(e)}"
        )

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No user profile configuration discovered. Complete onboarding form registration."
        )

    user_data = user_doc.to_dict()

    # ⚡ DEVELOPER BYPASS OVERRIDE
    if user_data.get("role") == "admin":
        print(f"⚡ Admin Bypass: Granting direct free access to Grade {requested_grade}.")
        return True

    # Subscription Verification
    sub_info = user_data.get("subscription", {})
    if not sub_info.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Access locked. Active standard subscription required (臨500/month)."
        )

    # Chronological Expiration Check
    expiry_str = sub_info.get("current_period_end")
    if expiry_str:
        expiry_date = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expiry_date:
            db.collection("users").document(user_id).update(
                {"subscription.is_active": False},
                timeout=FIRESTORE_TIMEOUT_SECONDS,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Your monthly subscription has expired. Please process renewal options."
            )

    # Role-Based Grade Enforcer
    if str(sub_info.get("subscribed_grade")) != str(requested_grade):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied. Current subscription active for Grade {sub_info.get('subscribed_grade')}."
        )

    return True
