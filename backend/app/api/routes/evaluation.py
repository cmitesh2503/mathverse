from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader

from ...agents.chapter_test_agent import chapter_test_agent
from ...services.bulk_evaluator import evaluate_submission
from ...services.firebase_service import (
    get_evaluation_records_by_test,
    get_evaluation_records_by_student,
    save_evaluation_record,
)
from ...services.retrieval_service import embed_text, retrieve_context
from ...services.session_service import session_service


router = APIRouter(tags=["Evaluation"])
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "data" / "evaluation_uploads"


def _safe_slug(value: str) -> str:
    clean = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value.strip())
    return clean or "unknown"


def _save_answer_sheet_image(*, test_id: str, student_id: str, source_filename: str | None, image_bytes: bytes) -> str:
    ext = Path(source_filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    relative_dir = Path(_safe_slug(test_id)) / _safe_slug(student_id)
    target_dir = UPLOAD_ROOT / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}{ext}"
    target_path = target_dir / target_name
    target_path.write_bytes(image_bytes)
    return f"/uploads/evaluation/{relative_dir.as_posix()}/{target_name}"


def _save_test_material_file(*, test_id: str, source_filename: str | None, file_bytes: bytes, doc_kind: str) -> str:
    ext = Path(source_filename or "").suffix.lower()
    if ext != ".pdf":
        ext = ".pdf"
    relative_dir = Path("test_materials") / _safe_slug(test_id)
    target_dir = UPLOAD_ROOT / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{doc_kind}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}{ext}"
    target_path = target_dir / target_name
    target_path.write_bytes(file_bytes)
    return f"/uploads/evaluation/{relative_dir.as_posix()}/{target_name}"


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return "\n".join(part for part in pages if part).strip()


def _chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    compact = " ".join(text.split())
    if not compact:
        return []
    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(compact):
        chunks.append(compact[start : start + chunk_size])
        start += step
    return chunks


def _index_test_material_chunks(*, test_id: str, test_name: str, test_number: int, doc_kind: str, text: str) -> int:
    import chromadb

    chunks = _chunk_text(text)
    if not chunks:
        return 0

    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="cbse_curriculum")

    for index, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        collection.add(
            ids=[f"{test_id}_{doc_kind}_{uuid.uuid4().hex[:10]}_{index}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[
                {
                    "test_id": test_id,
                    "test_name": test_name,
                    "test_number": int(test_number),
                    "doc_kind": doc_kind,
                    "source": "evaluation_test_material",
                }
            ],
        )
    return len(chunks)


class ChapterTestSubmission(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


@router.get("/evaluation/chapter-test/{session_id}")
def get_chapter_test(session_id: str, refresh: bool = False):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return chapter_test_agent.get_or_create(session, refresh=refresh)


@router.post("/evaluation/chapter-test/{session_id}/submit")
def submit_chapter_test(session_id: str, submission: ChapterTestSubmission):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        result = chapter_test_agent.evaluate(session_id, submission.answers)
    except KeyError:
        chapter_test_agent.get_or_create(session)
        result = chapter_test_agent.evaluate(session_id, submission.answers)

    return {"result": result}


@router.post("/api/evaluation/upload-test-materials")
async def upload_test_materials(
    test_id: str = Form(...),
    test_name: str = Form(...),
    test_number: int = Form(...),
    question_paper: UploadFile = File(...),
    marking_scheme: UploadFile = File(...),
):
    if not question_paper.filename or not question_paper.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="question_paper must be a PDF.")
    if not marking_scheme.filename or not marking_scheme.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="marking_scheme must be a PDF.")

    try:
        question_bytes = await question_paper.read()
        scheme_bytes = await marking_scheme.read()
        question_text = _extract_text_from_pdf_bytes(question_bytes)
        scheme_text = _extract_text_from_pdf_bytes(scheme_bytes)
        if not question_text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in question_paper PDF.")
        if not scheme_text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in marking_scheme PDF.")

        question_url = _save_test_material_file(
            test_id=test_id,
            source_filename=question_paper.filename,
            file_bytes=question_bytes,
            doc_kind="question_paper",
        )
        scheme_url = _save_test_material_file(
            test_id=test_id,
            source_filename=marking_scheme.filename,
            file_bytes=scheme_bytes,
            doc_kind="marking_scheme",
        )

        qp_chunks = _index_test_material_chunks(
            test_id=test_id,
            test_name=test_name,
            test_number=test_number,
            doc_kind="question_paper",
            text=question_text,
        )
        ms_chunks = _index_test_material_chunks(
            test_id=test_id,
            test_name=test_name,
            test_number=test_number,
            doc_kind="marking_scheme",
            text=scheme_text,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to upload/index test materials: {error}") from error

    return {
        "test_id": test_id,
        "test_name": test_name,
        "test_number": test_number,
        "question_paper_url": question_url,
        "marking_scheme_url": scheme_url,
        "indexed_chunks": {
            "question_paper": qp_chunks,
            "marking_scheme": ms_chunks,
            "total": qp_chunks + ms_chunks,
        },
    }


@router.post("/api/evaluation/bulk-upload")
async def bulk_upload_evaluation(
    test_id: str = Form(...),
    student_id: str = Form(...),
    student_name: str = Form(...),
    test_name: str = Form(...),
    test_number: int = Form(...),
    max_test_marks: float | None = Form(None),
    answer_sheet: UploadFile = File(...),
):
    preloaded_context = retrieve_context(
        topic=f"CBSE test rules for test_id={test_id}; question paper; marking scheme",
        n_results=3,
        metadata_filter={"test_id": test_id},
    )
    if not preloaded_context.strip():
        raise HTTPException(
            status_code=400,
            detail="Question paper and marking scheme are not indexed for this test_id. Upload both first via /api/evaluation/upload-test-materials.",
        )

    try:
        raw_image_bytes = await answer_sheet.read()
        payload = evaluate_submission(
            test_id=test_id,
            student_id=student_id,
            student_name=student_name,
            raw_image_bytes=raw_image_bytes,
            test_name=test_name,
            test_number=test_number,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Bulk evaluation failed: {error}") from error

    payload["evaluated_at"] = datetime.now(timezone.utc).isoformat()
    payload["source_filename"] = answer_sheet.filename
    payload["answer_sheet_image_url"] = _save_answer_sheet_image(
        test_id=test_id,
        student_id=student_id,
        source_filename=answer_sheet.filename,
        image_bytes=raw_image_bytes,
    )
    if max_test_marks is not None and float(max_test_marks) > 0:
        payload["total_maximum_marks"] = round(float(max_test_marks), 2)
        secured = float(payload.get("total_secured_marks", 0) or 0)
        payload["percentage_secured"] = f"{(secured / float(max_test_marks) * 100):.2f}%"
    save_evaluation_record(payload)
    return payload


@router.get("/api/evaluation/dashboard/{test_id}")
def evaluation_dashboard(
    test_id: str,
    page: int = 1,
    page_size: int = 25,
    max_test_marks: float | None = None,
):
    records = get_evaluation_records_by_test(test_id)
    page = max(1, page)
    page_size = max(1, min(250, page_size))

    total_students = len(records)
    resolved_max_marks = max_test_marks
    if resolved_max_marks is None:
        inferred = [float(record.get("total_maximum_marks", 0) or 0) for record in records if float(record.get("total_maximum_marks", 0) or 0) > 0]
        resolved_max_marks = max(inferred, default=0.0)

    total_marks = sum(float(record.get("total_secured_marks", 0) or 0) for record in records)
    class_average_percentage = (
        (total_marks / (total_students * resolved_max_marks)) * 100
        if total_students and resolved_max_marks > 0
        else 0.0
    )

    sorted_records = sorted(records, key=lambda record: str(record.get("student_id", "")))
    start = (page - 1) * page_size
    end = start + page_size
    paged_records = sorted_records[start:end]
    total_pages = (total_students + page_size - 1) // page_size if total_students else 0

    matrix_rows = []
    for record in paged_records:
        secured_marks = float(record.get("total_secured_marks", 0) or 0)
        max_marks = float(record.get("total_maximum_marks", 0) or resolved_max_marks or 0)
        percentage = (secured_marks / max_marks) * 100 if max_marks > 0 else 0.0
        matrix_rows.append(
            {
                "student_id": record.get("student_id", ""),
                "student_name": record.get("student_name", ""),
                "secured_marks": round(secured_marks, 2),
                "max_test_marks": round(max_marks, 2),
                "percentage": round(percentage, 2),
                "test_name": record.get("test_name", ""),
                "test_number": record.get("test_number"),
            }
        )

    summary = [{"student_id": record.get("student_id", "")} for record in sorted_records]

    return {
        "test_id": test_id,
        "test_name": (records[0].get("test_name") if records else ""),
        "test_number": (records[0].get("test_number") if records else None),
        "total_students": total_students,
        "class_average": round(class_average_percentage, 2),
        "max_test_marks": round(float(resolved_max_marks or 0), 2),
        "evaluated_students": summary,
        "score_matrix": matrix_rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_students,
            "showing_from": start + 1 if paged_records else 0,
            "showing_to": start + len(paged_records),
        },
    }


@router.get("/api/evaluation/student/{student_id}/marksheet")
def student_marksheet(student_id: str):
    records = get_evaluation_records_by_student(student_id)
    records_sorted = sorted(
        records,
        key=lambda record: (
            str(record.get("test_id", "")),
            str(record.get("evaluated_at", "")),
        ),
        reverse=True,
    )

    tests = []
    for record in records_sorted:
        max_marks = float(record.get("total_maximum_marks", 0) or 0)
        secured = float(record.get("total_secured_marks", 0) or 0)
        percentage = (secured / max_marks) * 100 if max_marks > 0 else 0.0

        tests.append(
            {
                "test_id": record.get("test_id", ""),
                "test_name": record.get("test_name", ""),
                "test_number": record.get("test_number"),
                "student_id": record.get("student_id", ""),
                "student_name": record.get("student_name", ""),
                "secured_marks": round(secured, 2),
                "max_test_marks": round(max_marks, 2),
                "percentage": round(percentage, 2),
                "percentage_secured": record.get("percentage_secured", f"{percentage:.2f}%"),
                "evaluated_at": record.get("evaluated_at"),
                "concept_mastery_insights": record.get("concept_mastery_insights", {"strong_concepts": [], "weak_concepts": []}),
                "answer_sheet_image_url": record.get("answer_sheet_image_url"),
            }
        )

    return {
        "student_id": student_id,
        "total_tests": len(tests),
        "marksheet": tests,
    }


@router.get("/api/evaluation/student/{student_id}/tests/{test_id}/breakdown")
def student_test_breakdown(student_id: str, test_id: str):
    records = get_evaluation_records_by_student(student_id)
    matched = [record for record in records if str(record.get("test_id", "")) == test_id]
    if not matched:
        raise HTTPException(status_code=404, detail="Evaluation record not found for this student and test.")

    latest = sorted(matched, key=lambda record: str(record.get("evaluated_at", "")), reverse=True)[0]
    max_marks = float(latest.get("total_maximum_marks", 0) or 0)
    secured = float(latest.get("total_secured_marks", 0) or 0)
    percentage = (secured / max_marks) * 100 if max_marks > 0 else 0.0

    return {
        "test_id": latest.get("test_id", ""),
        "test_name": latest.get("test_name", ""),
        "test_number": latest.get("test_number"),
        "student_id": latest.get("student_id", ""),
        "student_name": latest.get("student_name", ""),
        "secured_marks": round(secured, 2),
        "max_test_marks": round(max_marks, 2),
        "percentage": round(percentage, 2),
        "percentage_secured": latest.get("percentage_secured", f"{percentage:.2f}%"),
        "evaluated_at": latest.get("evaluated_at"),
        "concept_mastery_insights": latest.get("concept_mastery_insights", {"strong_concepts": [], "weak_concepts": []}),
        "answer_sheet_image_url": latest.get("answer_sheet_image_url"),
        "detailed_answer_breakdown": latest.get("detailed_answer_breakdown", []),
    }
