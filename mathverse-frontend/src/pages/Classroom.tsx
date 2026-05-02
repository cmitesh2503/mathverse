"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PageKey } from "../App";
import { TutorAvatar } from "../components/TutorAvatar";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { Whiteboard } from "../components/Whiteboard";
import { useTutorStream } from "../hooks/useTutorStream";
import type { ClassResponse } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function Classroom({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const plan = useTutorStore((state) => state.plan);
  const setCurrentTopic = useTutorStore((state) => state.setCurrentTopic);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const setHomeworkQuestions = useTutorStore((state) => state.setHomeworkQuestions);
  const pendingClassResponse = useTutorStore((state) => state.pendingClassResponse);
  const setPendingClassResponse = useTutorStore((state) => state.setPendingClassResponse);
  const recordTutorSession = useTutorStore((state) => state.recordTutorSession);
  const recordResponse = useTutorStore((state) => state.recordResponse);
  const [answer, setAnswer] = useState("");
  const consumedPendingRef = useRef(false);

  const onResponse = useCallback(
    (data: ClassResponse) => {
      const nextTopic = data.topic || data.chapter || data.content?.chapter;
      if (nextTopic) {
        setCurrentTopic(nextTopic);
      }
      setCurrentConcept(data.concept || data.content?.concept || null);
      if (data.question || data.example || data.content?.question || data.content?.example) {
        setCurrentQuestion(data.question || data.example || data.content?.question || data.content?.example || "");
      }
      const homework = data.homework || data.content?.homework || data.content?.questions || [];
      if (homework.length) {
        setHomeworkQuestions(homework);
      } else if (data.type !== "homework") {
        setHomeworkQuestions([]);
      }
      if (data.type === "evaluation" && data.correct !== null && data.correct !== undefined) {
        recordResponse({
          correct: data.correct,
          mistake_type: data.mistake_type,
          hint: data.hint,
          explanation: data.explanation,
          steps: data.steps,
          shortcut: data.shortcut,
          speed_hint: data.speed_hint,
          next_question: data.question,
        });
      }
      recordTutorSession({
        concept: data.concept || data.content?.concept,
        mistake_type: data.mistake_type,
        pattern: examMode === "jee" ? data.pattern || data.content?.pattern : null,
      });
    },
    [examMode, recordResponse, recordTutorSession, setCurrentConcept, setCurrentQuestion, setCurrentTopic, setHomeworkQuestions],
  );

  const { response, visibleSteps, isSpeaking, loading, error, paused, start, pauseOrResume, prime } = useTutorStream({
    sessionId,
    examMode,
    onResponse,
  });

  const theme = useMemo(
    () =>
      examMode === "jee"
        ? { page: "bg-orange-50", panel: "border-orange-200 from-orange-50", button: "bg-orange-600 hover:bg-orange-700" }
        : { page: "bg-blue-50", panel: "border-blue-200 from-blue-50", button: "bg-blue-600 hover:bg-blue-700" },
    [examMode],
  );

  const classAllowed = examMode === "cbse" ? canUseFeature(plan, "cbse_class") : canUseFeature(plan, "jee_practice");

  useEffect(() => {
    if (!classAllowed) return;
    if (pendingClassResponse) {
      consumedPendingRef.current = true;
      prime(pendingClassResponse);
      onResponse(pendingClassResponse);
      setPendingClassResponse(null);
      return;
    }
    if (consumedPendingRef.current) return;
    void start({ grade: 10, subject: "math" });
  }, [classAllowed, examMode, onResponse, pendingClassResponse, prime, setPendingClassResponse, start]);

  const concept = response?.concept || response?.content?.concept || "Starting class";
  const explanation = response?.explanation || response?.content?.explanation || "Class explanation will appear here.";
  const example = response?.example || response?.content?.example;
  const pattern = response?.pattern || response?.content?.pattern;
  const shortcut = response?.shortcut || response?.content?.shortcut;
  const speedHint = response?.speed_hint || response?.content?.speed_hint;
  const whiteboard = response?.whiteboard || response?.content?.whiteboard;
  const notes = response?.session_notes || response?.content?.session_notes || response?.note_cards || response?.content?.note_cards || [];
  const homework = response?.homework || response?.content?.homework || response?.content?.questions || [];
  const isQuestion = response?.type === "question";
  const nextLabel =
    response?.next_action === "board_example"
      ? "Show Board Example"
      : response?.next_action === "question"
        ? "Ask Mini Check"
        : response?.next_action === "homework" || response?.type === "homework"
          ? "Open Homework"
          : "Next";

  async function submitClassAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || loading) return;
    await start({ action: "next", answer });
    setAnswer("");
  }

  function goNext() {
    if (response?.type === "homework") {
      onNavigate("homework");
      return;
    }
    void start({ action: "next" });
  }

  return (
    <main className={`min-h-[calc(100vh-4rem)] ${theme.page}`}>
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        {!classAllowed && (
          <div className="lg:col-span-2">
            <UpgradeNotice
              title={examMode === "jee" ? "JEE class mode is included in JEE Pro" : "Full voice classroom is included in CBSE Pro"}
              description="Free includes basic CBSE practice. Upgrade the active plan to unlock guided whiteboard classes, synced avatar voice, and saved class notes."
              recommendedPlan={examMode === "jee" ? "jee_pro" : "cbse_pro"}
            />
          </div>
        )}

        {classAllowed && (
          <>
        <section className={`rounded-2xl border bg-gradient-to-br ${theme.panel} to-white p-5 shadow-md`}>
          <TutorAvatar
            isSpeaking={isSpeaking}
            label="Live AI Class"
            text={loading ? "Starting class..." : isSpeaking ? "Teaching with voice" : paused ? "Paused" : "Ready"}
          />

          <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold uppercase text-slate-500">Chapter Flow</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">{response?.chapter || response?.content?.chapter || "Chapter 1"}</h1>
            <p className="mt-1 text-xs font-semibold uppercase text-slate-400">{response?.chapter_label || response?.content?.chapter_label || "Starting"}</p>
            <p className="mt-2 text-sm font-medium text-slate-600">{concept}</p>
          </div>

          <div className="mt-4 rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold text-slate-950">Voice Stream</p>
            <p className="mt-2 text-sm text-slate-600">
              {loading
                ? "Preparing..."
                : isSpeaking
                  ? `${response?.avatar_voice?.pace || response?.content?.avatar_voice?.pace || "slow"} voice with whiteboard sync`
                  : paused
                    ? "Paused"
                    : "Ready"}
            </p>
          </div>

          {notes.length > 0 && (
            <div className="mt-4 rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-slate-200">
              <p className="text-sm font-semibold text-slate-950">Important Notes</p>
              <ul className="mt-2 space-y-2 text-sm text-slate-600">
                {notes.slice(0, 4).map((note) => (
                  <li key={note}>- {note}</li>
                ))}
              </ul>
            </div>
          )}

          {error && <div className="mt-4 rounded-2xl border border-rose-200 bg-white p-4 text-sm text-rose-700">{error}</div>}

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={pauseOrResume}
              disabled={loading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              Pause
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={loading || isQuestion}
              className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition disabled:bg-slate-300 ${theme.button}`}
            >
              {nextLabel}
            </button>
            <button
              type="button"
              onClick={() => void start({ action: "repeat" })}
              disabled={loading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              Repeat
            </button>
            <button
              type="button"
              onClick={() => void start({ action: "homework" })}
              disabled={loading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              End With Homework
            </button>
          </div>
        </section>

        <section className="space-y-5">
          <Whiteboard steps={visibleSteps} whiteboard={whiteboard} />

          {examMode === "jee" && (
            <div className="rounded-2xl border border-orange-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">Pattern Recognition</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl bg-orange-50 p-4 text-sm text-orange-900">
                  <p className="font-semibold">Pattern</p>
                  <p className="mt-2">{pattern || "Quadratic pattern"}</p>
                </div>
                <div className="rounded-2xl bg-orange-50 p-4 text-sm text-orange-900">
                  <p className="font-semibold">Detection logic</p>
                  <p className="mt-2">{speedHint || "Identify the algebraic form before expanding."}</p>
                </div>
                <div className="rounded-2xl bg-orange-50 p-4 text-sm text-orange-900">
                  <p className="font-semibold">Shortcut</p>
                  <p className="mt-2">{shortcut || "Factor before using formula."}</p>
                </div>
              </div>
            </div>
          )}

          {examMode === "cbse" && (
            <div className="rounded-2xl border border-blue-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">Concept Teaching</h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">{explanation}</p>
              {example && <p className="mt-4 rounded-2xl bg-blue-50 p-4 font-mono text-sm font-semibold text-blue-900">{example}</p>}
            </div>
          )}

          {response?.type === "question" && (
            <form onSubmit={submitClassAnswer} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">Mini Check</h2>
              <p className="mt-2 font-mono text-base font-semibold text-slate-800">{response.question || response.content?.question}</p>
              {response.hint && <p className="mt-2 text-sm text-slate-500">Hint: {response.hint}</p>}
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <input
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="Type your answer"
                  className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-950 outline-none ring-slate-900 transition focus:ring-2"
                />
                <button
                  type="submit"
                  disabled={loading || !answer.trim()}
                  className={`rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-sm transition disabled:bg-slate-300 ${theme.button}`}
                >
                  Submit Answer
                </button>
              </div>
            </form>
          )}

          {response?.type === "homework" && (
            <div className="rounded-2xl border border-emerald-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">Homework Ready</h2>
              <div className="mt-4 space-y-2">
                {homework.slice(0, 5).map((question, index) => (
                  <div key={`${question.prompt || question.question || index}`} className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
                    {index + 1}. {question.prompt || question.question || "Practice question"}
                  </div>
                ))}
              </div>
              <div className="mt-5 flex justify-end">
                <button
                  type="button"
                  onClick={() => void start({ action: "skip_homework" })}
                  disabled={loading}
                  className="mr-3 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:text-slate-300"
                >
                  Skip Homework
                </button>
                <button
                  type="button"
                  onClick={() => onNavigate("homework")}
                  className="rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
                >
                  Open Homework
                </button>
              </div>
            </div>
          )}

          {response?.type === "evaluation" && (
            <div className={`rounded-2xl border bg-white p-5 shadow-md ${response.correct ? "border-emerald-200" : "border-rose-200"}`}>
              <h2 className="text-lg font-semibold text-slate-950">{response.correct ? "Correct" : "Needs Review"}</h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">{explanation}</p>
              <button
                type="button"
                onClick={() => void start({ action: "next" })}
                disabled={loading}
                className={`mt-4 rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-sm transition disabled:bg-slate-300 ${theme.button}`}
              >
                Continue
              </button>
            </div>
          )}
        </section>
          </>
        )}
      </div>
    </main>
  );
}
