"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { sendAnswer, type LearnResponse, type TutorResponse } from "../services/api";
import { useTutorStore } from "../store/useTutorStore";
import type { PageKey } from "../App";

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function Learn({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const currentTopic = useTutorStore((state) => state.currentTopic);
  const currentConcept = useTutorStore((state) => state.currentConcept);
  const setCurrentTopic = useTutorStore((state) => state.setCurrentTopic);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const recordResponse = useTutorStore((state) => state.recordResponse);

  const [topic, setTopic] = useState(currentTopic);
  const [lesson, setLesson] = useState<LearnResponse | null>(null);
  const [answer, setAnswer] = useState("");
  const [checkResult, setCheckResult] = useState<TutorResponse | null>(null);
  const [loadingLesson, setLoadingLesson] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const theme = useMemo(
    () =>
      examMode === "jee"
        ? {
            page: "bg-orange-50",
            ring: "border-orange-200",
            chip: "bg-orange-100 text-orange-800",
            button: "bg-orange-600 hover:bg-orange-700",
          }
        : {
            page: "bg-blue-50",
            ring: "border-blue-200",
            chip: "bg-blue-100 text-blue-800",
            button: "bg-blue-600 hover:bg-blue-700",
          },
    [examMode],
  );

  async function loadLesson(nextTopic = topic, action?: "next_concept" | "next_topic" | "continue") {
    setLoadingLesson(true);
    setError(null);
    setCheckResult(null);
    setAnswer("");

    try {
      const data = await sendAnswer<LearnResponse>({
        session_id: sessionId,
        mode: "learn",
        input: { question: nextTopic, topic: nextTopic, action },
        context: { exam: examMode },
      });

      setLesson(data);
      const resolvedTopic = data.topic || data.chapter || nextTopic;
      setTopic(resolvedTopic);
      setCurrentTopic(resolvedTopic);
      setCurrentConcept(data.concept || null);
      if (data.check_question) setCurrentQuestion(data.check_question);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load lesson");
    } finally {
      setLoadingLesson(false);
    }
  }

  async function submitQuickCheck(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lesson?.check_question || !answer.trim() || checking) return;

    setChecking(true);
    setError(null);

    try {
      const data = await sendAnswer<TutorResponse>({
        session_id: sessionId,
        mode: "practice",
        input: {
          question: lesson.check_question,
          answer,
        },
        context: { exam: examMode },
      });

      setCheckResult(data);
      recordResponse(data);
      if (data.next_question) {
        const parts = data.next_question.split("\n").map((part) => part.trim()).filter(Boolean);
        setCurrentQuestion(parts[parts.length - 1] || lesson.check_question);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to check answer");
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    setTopic(currentTopic);
    void loadLesson(currentTopic);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examMode, currentTopic]);

  return (
    <main className={`min-h-[calc(100vh-4rem)] ${theme.page}`}>
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-6 sm:px-6">
        <section className={`rounded-2xl border ${theme.ring} bg-white p-5 shadow-md`}>
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <label className="block">
              <span className="text-sm font-semibold text-slate-600">Topic</span>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 text-slate-950 outline-none transition focus:ring-2 focus:ring-slate-900"
              />
            </label>
            <div>
              <p className="text-sm font-semibold text-slate-600">Concept</p>
              <div className={`mt-2 rounded-xl px-3 py-3 text-sm font-semibold ${theme.chip}`}>
                {lesson?.concept || currentConcept || "Loading..."}
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setCurrentTopic(topic);
                onNavigate("tutor");
              }}
              className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition ${theme.button}`}
            >
              Open AI Tutor
            </button>
            <button
              type="button"
              onClick={() => void loadLesson(topic)}
              disabled={loadingLesson}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              {loadingLesson ? "Loading..." : "Load Concept"}
            </button>
            <button
              type="button"
              onClick={() => onNavigate("practice")}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Practice
            </button>
          </div>
        </section>

        {error && <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-rose-700 shadow-md">{error}</div>}

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
          <h2 className="text-lg font-semibold text-slate-950">Brain Explanation</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
            {loadingLesson ? "Preparing lesson..." : lesson?.explanation || "Choose a topic to start learning."}
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
          <h2 className="text-lg font-semibold text-slate-950">Book Example</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
            {lesson?.example || "An example will appear after the concept loads."}
          </p>
          {!!lesson?.steps?.length && (
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-slate-700">
              {lesson.steps.map((step, index) => (
                <li key={`${step}-${index}`}>{step}</li>
              ))}
            </ol>
          )}
          {lesson?.shortcut && (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-semibold">Shortcut</p>
              <p className="mt-1">{lesson.shortcut}</p>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
          <h2 className="text-lg font-semibold text-slate-950">Quick Check</h2>
          <p className="mt-3 rounded-2xl bg-slate-50 p-4 text-base font-semibold text-slate-950">
            {lesson?.check_question || "Quick check question will appear here."}
          </p>

          <form onSubmit={submitQuickCheck} className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="Enter answer"
              className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-3 outline-none transition focus:ring-2 focus:ring-slate-900"
            />
            <button
              type="submit"
              disabled={checking || !answer.trim() || !lesson?.check_question}
              className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {checking ? "Checking..." : "Submit"}
            </button>
          </form>

          {checkResult && (
            <div
              className={`mt-4 rounded-2xl p-4 text-sm font-semibold ${
                checkResult.correct ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
              }`}
            >
              {checkResult.correct ? "Correct. You can move to the next concept." : checkResult.hint || "Review the explanation and try again."}
            </div>
          )}
        </section>

        <section className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void loadLesson(topic, "next_concept")}
            disabled={!lesson || loadingLesson}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          >
            Next Concept
          </button>
          <button
            type="button"
            onClick={() => void loadLesson(topic, "next_topic")}
            disabled={!lesson || loadingLesson}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          >
            Next Topic
          </button>
          <button
            type="button"
            onClick={() => onNavigate("practice")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition ${theme.button}`}
          >
            Practice
          </button>
        </section>
      </div>
    </main>
  );
}
