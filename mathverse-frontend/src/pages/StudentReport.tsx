"use client";

import { useMemo, useState } from "react";
import type { PageKey } from "../App";
import {
  API_BASE_URL,
  getStudentMarksheet,
  getStudentTestBreakdown,
  uploadAnswerSheet,
  uploadTestMaterials,
  type DetailedAnswerEntry,
  type StudentBreakdownResponse,
  type StudentMarksheetEntry,
} from "../services/api";

function rankLabel(score: number) {
  if (score >= 90) return "Outstanding";
  if (score >= 75) return "Very Good";
  if (score >= 60) return "Good Progress";
  if (score >= 40) return "Needs Focus";
  return "Critical Revision";
}

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function StudentReport({ onNavigate }: Props) {
  const [studentId, setStudentId] = useState("STU_88D294");
  const [marksheet, setMarksheet] = useState<StudentMarksheetEntry[]>([]);
  const [selected, setSelected] = useState<StudentMarksheetEntry | null>(null);
  const [breakdown, setBreakdown] = useState<StudentBreakdownResponse | null>(null);
  const [selectedQuestion, setSelectedQuestion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"overview" | "review">("overview");
  const [uploadTestId, setUploadTestId] = useState("cbse_math_mock_2026");
  const [uploadTestName, setUploadTestName] = useState("CBSE Math Term-1 Mock");
  const [uploadTestNumber, setUploadTestNumber] = useState(1);
  const [uploadStudentId, setUploadStudentId] = useState("STU_88D294");
  const [uploadStudentName, setUploadStudentName] = useState("Mitesh Chokshi");
  const [uploadMaxMarks, setUploadMaxMarks] = useState(80);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [questionPaperFile, setQuestionPaperFile] = useState<File | null>(null);
  const [markingSchemeFile, setMarkingSchemeFile] = useState<File | null>(null);
  const [materialUploading, setMaterialUploading] = useState(false);
  const [materialsMessage, setMaterialsMessage] = useState<string | null>(null);

  const selectedDetail: DetailedAnswerEntry | null = useMemo(() => {
    if (!breakdown?.detailed_answer_breakdown?.length) return null;
    return breakdown.detailed_answer_breakdown[selectedQuestion] || breakdown.detailed_answer_breakdown[0];
  }, [breakdown, selectedQuestion]);
  const answerSheetImageSrc = useMemo(() => {
    const raw = breakdown?.answer_sheet_image_url;
    if (!raw) return null;
    if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
    return `${API_BASE_URL.replace(/\/$/, "")}${raw.startsWith("/") ? raw : `/${raw}`}`;
  }, [breakdown?.answer_sheet_image_url]);

  async function loadMarksheet() {
    setLoading(true);
    setError(null);
    try {
      const payload = await getStudentMarksheet(studentId.trim());
      setMarksheet(payload.marksheet || []);
      setSelected(payload.marksheet?.[0] || null);
      setBreakdown(null);
      setView("overview");
      setSelectedQuestion(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load marksheet.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!uploadFile) {
      setUploadMessage("Please choose an answer-sheet image file.");
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    setError(null);
    try {
      await uploadAnswerSheet({
        test_id: uploadTestId.trim(),
        test_name: uploadTestName.trim(),
        test_number: uploadTestNumber,
        student_id: uploadStudentId.trim(),
        student_name: uploadStudentName.trim(),
        max_test_marks: uploadMaxMarks,
        answer_sheet: uploadFile,
      });
      setStudentId(uploadStudentId.trim());
      setUploadMessage("Upload and evaluation completed.");
      const payload = await getStudentMarksheet(uploadStudentId.trim());
      setMarksheet(payload.marksheet || []);
      setSelected(payload.marksheet?.[0] || null);
      setBreakdown(null);
      setView("overview");
      setSelectedQuestion(0);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed.";
      setError(msg);
      setUploadMessage(msg);
    } finally {
      setUploading(false);
    }
  }

  async function handleMaterialsUpload() {
    if (!questionPaperFile || !markingSchemeFile) {
      setMaterialsMessage("Please select both Question Paper PDF and Marking Scheme PDF.");
      return;
    }
    setMaterialUploading(true);
    setMaterialsMessage(null);
    setError(null);
    try {
      await uploadTestMaterials({
        test_id: uploadTestId.trim(),
        test_name: uploadTestName.trim(),
        test_number: uploadTestNumber,
        question_paper: questionPaperFile,
        marking_scheme: markingSchemeFile,
      });
      setMaterialsMessage("Question paper and marking scheme uploaded and indexed successfully.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to upload test materials.";
      setError(msg);
      setMaterialsMessage(msg);
    } finally {
      setMaterialUploading(false);
    }
  }

  async function openBreakdown(entry: StudentMarksheetEntry) {
    setLoading(true);
    setError(null);
    try {
      const detail = await getStudentTestBreakdown(studentId.trim(), entry.test_id);
      setSelected(entry);
      setBreakdown(detail);
      setSelectedQuestion(0);
      setView("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load test breakdown.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-slate-900">MathVerse Student Report Center</h1>
          <button onClick={() => onNavigate("home")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Back to Dashboard</button>
        </div>
        <div className="mt-4 flex gap-2">
          <input value={studentId} onChange={(e) => setStudentId(e.target.value)} placeholder="Student ID" className="w-56 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={() => void loadMarksheet()} disabled={loading} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">{loading ? "Loading..." : "Load Reports"}</button>
        </div>
        {error && <p className="mt-3 text-sm text-rose-700">{error}</p>}
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-bold text-amber-900">Temporary Admin Upload Panel</h2>
          <span className="rounded-full bg-amber-200 px-3 py-1 text-xs font-semibold text-amber-900">Move later to Class Admin Interface</span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <input value={uploadTestId} onChange={(e) => setUploadTestId(e.target.value)} placeholder="Test ID" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input value={uploadTestName} onChange={(e) => setUploadTestName(e.target.value)} placeholder="Test Name" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input type="number" value={uploadTestNumber} onChange={(e) => setUploadTestNumber(Number(e.target.value || 0))} placeholder="Test Number" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input value={uploadStudentId} onChange={(e) => setUploadStudentId(e.target.value)} placeholder="Student ID" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input value={uploadStudentName} onChange={(e) => setUploadStudentName(e.target.value)} placeholder="Student Name" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input type="number" value={uploadMaxMarks} onChange={(e) => setUploadMaxMarks(Number(e.target.value || 0))} placeholder="Max Test Marks" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <input type="file" accept="image/*" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} className="md:col-span-2 rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
          <button onClick={() => void handleUpload()} disabled={uploading} className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:bg-amber-400">
            {uploading ? "Uploading..." : "Upload & Evaluate"}
          </button>
        </div>
        <div className="mt-5 rounded-xl border border-amber-300 bg-white p-4">
          <p className="text-sm font-semibold text-amber-900">Step 1: Upload Test Materials (Required before answer-sheet evaluation)</p>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <input type="file" accept=".pdf,application/pdf" onChange={(e) => setQuestionPaperFile(e.target.files?.[0] || null)} className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
            <input type="file" accept=".pdf,application/pdf" onChange={(e) => setMarkingSchemeFile(e.target.files?.[0] || null)} className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm" />
            <button onClick={() => void handleMaterialsUpload()} disabled={materialUploading} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900 disabled:bg-slate-400">
              {materialUploading ? "Indexing..." : "Upload Question Paper + Marking Scheme"}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-600">First file: Question Paper PDF. Second file: CBSE Marking Scheme PDF.</p>
          {materialsMessage && <p className="mt-2 text-sm text-amber-900">{materialsMessage}</p>}
        </div>
        <p className="mt-3 text-sm font-semibold text-amber-900">Step 2: Upload each student answer sheet for evaluation</p>
        {uploadMessage && <p className="mt-3 text-sm text-amber-900">{uploadMessage}</p>}
      </section>

      {view === "overview" && selected && (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-600">Test: {selected.test_name} | Date Evaluated: {(selected.evaluated_at || "").slice(0, 10)}</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">YOUR SCORE</p><p className="text-2xl font-bold">{selected.secured_marks} / {selected.max_test_marks}</p></div>
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">PERCENTAGE</p><p className="text-2xl font-bold">{selected.percentage_secured}</p></div>
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">ACCURACY RANK</p><p className="text-2xl font-bold">{rankLabel(selected.percentage)}</p></div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold">Concept Mastery Matrix (AI Insights)</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="font-semibold text-emerald-800">Strengths (Excellent Work)</p>
                <ul className="mt-2 space-y-2 text-sm text-emerald-900">
                  {(selected.concept_mastery_insights?.strong_concepts || []).map((item) => <li key={item}>- {item}</li>)}
                </ul>
              </div>
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                <p className="font-semibold text-rose-800">Weak Areas (Let's Revise These)</p>
                <ul className="mt-2 space-y-2 text-sm text-rose-900">
                  {(selected.concept_mastery_insights?.weak_concepts || []).map((item) => <li key={item}>- {item}</li>)}
                </ul>
              </div>
            </div>
            <button onClick={() => void openBreakdown(selected)} className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">View Itemized Script Markup & Step-by-Step Corrections</button>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold">All Tests</h3>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="text-left text-slate-500"><th className="py-2">Test</th><th>Secured</th><th>Percentage</th><th /></tr></thead>
                <tbody>
                  {marksheet.map((item) => (
                    <tr key={`${item.test_id}-${item.evaluated_at}`} className="border-t border-slate-100">
                      <td className="py-2">{item.test_name} #{item.test_number ?? "-"}</td>
                      <td>{item.secured_marks} / {item.max_test_marks}</td>
                      <td>{item.percentage_secured}</td>
                      <td><button onClick={() => void openBreakdown(item)} className="rounded-md border border-slate-300 px-2 py-1">View Paper Breakdown</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {view === "review" && breakdown && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <button onClick={() => setView("overview")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Back to Overview</button>
            <p className="text-sm text-slate-600">Exam Review Mode</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold">Your Scanned Paper Markup</p>
              {answerSheetImageSrc ? (
                <div className="mt-3 space-y-3">
                  <img
                    src={answerSheetImageSrc}
                    alt={`Scanned paper for ${breakdown.student_name}`}
                    className="max-h-[36rem] w-full rounded-lg border border-slate-300 bg-white object-contain"
                  />
                  {selectedDetail && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                      <p className="font-semibold">Active Annotation: {selectedDetail.question_number}</p>
                      <p className="mt-1">{selectedDetail.step_by_step_audit}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-3 min-h-80 rounded-lg border border-dashed border-slate-300 bg-white p-3 text-sm text-slate-600">
                  No scanned paper image found for this evaluation record.
                </div>
              )}
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap gap-2">
                {breakdown.detailed_answer_breakdown.map((item, index) => (
                  <button key={`${item.question_number}-${index}`} onClick={() => setSelectedQuestion(index)} className={`rounded-md px-3 py-1 text-sm ${selectedQuestion === index ? "bg-slate-900 text-white" : "border border-slate-300"}`}>{item.question_number || `Q${index + 1}`}</button>
                ))}
              </div>
              {selectedDetail && (
                <div className="mt-4 space-y-3 text-sm">
                  <p className="font-semibold">{selectedDetail.question_number}: {selectedDetail.question_text}</p>
                  <p>Status: {selectedDetail.allocated_marks} / {selectedDetail.max_marks} Marks</p>
                  <div className="rounded-lg bg-white p-3">
                    <p>Formula & Given Data: {selectedDetail.step_wise_credits.formula_and_given_data}</p>
                    <p>Step Progression Lines: {selectedDetail.step_wise_credits.step_progression_lines}</p>
                    <p>Final Value & Units: {selectedDetail.step_wise_credits.final_value_and_units}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3">
                    <p className="font-semibold">Examiner Audit Note</p>
                    <p>{selectedDetail.step_by_step_audit}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3">
                    <p className="font-semibold">Arvind Sir's Actionable Advice</p>
                    <p>{selectedDetail.remediation_advice}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
