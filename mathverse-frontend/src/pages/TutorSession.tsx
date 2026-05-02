"use client";

import { useEffect, useMemo, useState } from "react";
import type { PageKey } from "../App";
import { TutorAvatar } from "../components/TutorAvatar";
import { Whiteboard } from "../components/Whiteboard";
import { sendAnswer, type LearnResponse } from "../services/api";
import { useTutorStore } from "../store/useTutorStore";
import { pauseSpeech, resumeSpeech, speak, stopSpeech } from "../utils/speak";

type Props = {
  onNavigate: (page: PageKey) => void;
};

function fallbackSteps(lesson: LearnResponse | null) {
  if (lesson?.steps?.length) return lesson.steps;
  if (lesson?.check_question) {
    return [lesson.check_question, "Identify the pattern.", "Solve carefully and verify the roots."];
  }
  return ["x^2 - 4 = 0", "x^2 = 4", "x = +/-2"];
}

function inferPattern(text: string) {
  const normalized = text.replace(/\s+/g, "").toLowerCase();
  if (normalized.includes("x^2-") || normalized.includes("x**2-")) return "Difference of Squares";
  if (normalized.includes("x^2") || normalized.includes("x**2")) return "Factorization";
  return "Quadratic Pattern";
}

export default function TutorSession({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const topic = useTutorStore((state) => state.currentTopic);
  const currentConcept = useTutorStore((state) => state.currentConcept);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const recordTutorSession = useTutorStore((state) => state.recordTutorSession);

  const [lesson, setLesson] = useState<LearnResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const theme = useMemo(
    () =>
      examMode === "jee"
        ? {
            page: "bg-orange-50",
            panel: "from-orange-50 to-white border-orange-200",
            chip: "bg-orange-100 text-orange-800",
            button: "bg-orange-600 hover:bg-orange-700",
          }
        : {
            page: "bg-blue-50",
            panel: "from-blue-50 to-white border-blue-200",
            chip: "bg-blue-100 text-blue-800",
            button: "bg-blue-600 hover:bg-blue-700",
          },
    [examMode],
  );

  const steps = useMemo(() => fallbackSteps(lesson), [lesson]);
  const explanation = lesson?.explanation || "Let us learn this concept step by step.";
  const pattern = inferPattern(lesson?.check_question || lesson?.example || topic);

  function playExplanation(text = explanation) {
    setPaused(false);
    setSpeaking(true);
    speak(text, () => setSpeaking(false));
  }

  useEffect(() => {
    async function loadTutorSession() {
      setLoading(true);
      setError(null);
      stopSpeech();
      setSpeaking(false);

      try {
        const data = await sendAnswer<LearnResponse>({
          session_id: sessionId,
          mode: "learn",
          input: { question: topic, topic },
          context: { exam: examMode },
        });

        setLesson(data);
        setCurrentConcept(data.concept || null);
        if (data.check_question) setCurrentQuestion(data.check_question);
        recordTutorSession({
          concept: data.concept,
          pattern: examMode === "jee" ? inferPattern(data.check_question || data.example || topic) : null,
        });
        playExplanation(data.explanation || "Let us learn this concept step by step.");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load tutor session");
      } finally {
        setLoading(false);
      }
    }

    void loadTutorSession();
    return () => stopSpeech();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examMode, sessionId, topic]);

  function togglePause() {
    if (paused) {
      resumeSpeech();
      setPaused(false);
      setSpeaking(true);
    } else {
      pauseSpeech();
      setPaused(true);
      setSpeaking(false);
    }
  }

  return (
    <main className={`min-h-[calc(100vh-4rem)] ${theme.page}`}>
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <section className={`rounded-2xl border bg-gradient-to-br ${theme.panel} p-5 shadow-md`}>
          <TutorAvatar speaking={speaking} />

          <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold uppercase text-slate-500">Topic</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">AI Tutor: {topic}</h1>
            <p className="mt-2 text-sm font-medium text-slate-600">{lesson?.concept || currentConcept || "Preparing lesson"}</p>
          </div>

          <div className="mt-4 rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold text-slate-950">🎙 Voice</p>
            <p className="mt-2 text-sm text-slate-600">
              {loading ? "Preparing explanation..." : speaking ? "Voice explanation playing" : paused ? "Paused" : "Explanation ready"}
            </p>
          </div>

          {error && <div className="mt-4 rounded-2xl border border-rose-200 bg-white p-4 text-sm text-rose-700">{error}</div>}

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => playExplanation()}
              disabled={loading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              ▶ Replay
            </button>
            <button
              type="button"
              onClick={togglePause}
              disabled={loading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:text-slate-300"
            >
              ⏸ Pause
            </button>
            <button
              type="button"
              onClick={() => onNavigate("practice")}
              className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition ${theme.button}`}
            >
              Next
            </button>
          </div>
        </section>

        <section className="space-y-5">
          <Whiteboard steps={loading ? [] : steps} />

          {examMode === "jee" ? (
            <div className="rounded-2xl border border-orange-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">🎯 Pattern Insight</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl bg-orange-50 p-4">
                  <p className="text-sm font-semibold text-orange-900">Pattern</p>
                  <p className="mt-2 text-sm text-orange-800">{pattern}</p>
                </div>
                <div className="rounded-2xl bg-orange-50 p-4">
                  <p className="text-sm font-semibold text-orange-900">Recognition Tip</p>
                  <p className="mt-2 font-mono text-sm text-orange-800">a^2 - b^2 = (a-b)(a+b)</p>
                </div>
                <div className="rounded-2xl bg-orange-50 p-4">
                  <p className="text-sm font-semibold text-orange-900">Speed Trick</p>
                  <p className="mt-2 font-mono text-sm text-orange-800">{lesson?.shortcut || "x^2 - 25 = (x-5)(x+5)"}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-blue-200 bg-white p-5 shadow-md">
              <h2 className="text-lg font-semibold text-slate-950">📘 Concept Explanation</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl bg-blue-50 p-4">
                  <p className="text-sm font-semibold text-blue-900">Definition</p>
                  <p className="mt-2 text-sm leading-6 text-blue-800">{lesson?.concept || "Quadratic concept"}</p>
                </div>
                <div className="rounded-2xl bg-blue-50 p-4 md:col-span-2">
                  <p className="text-sm font-semibold text-blue-900">Explanation</p>
                  <p className="mt-2 text-sm leading-6 text-blue-800">{explanation}</p>
                </div>
              </div>
              <div className="mt-4 rounded-2xl bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Example</p>
                <p className="mt-2 font-mono text-sm text-slate-700">{lesson?.example || lesson?.check_question || "x^2 - 4 = 0"}</p>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => onNavigate("practice")}
              className={`rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-sm transition ${theme.button}`}
            >
              Try Question
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
