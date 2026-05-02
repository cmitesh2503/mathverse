"use client";

import { FormEvent, useMemo, useState } from "react";
import { ResponsePanel } from "../components/ResponsePanel";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { sendAnswer } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

export default function Practice() {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const plan = useTutorStore((state) => state.plan);
  const currentConcept = useTutorStore((state) => state.currentConcept);
  const currentQuestion = useTutorStore((state) => state.current_question);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const lastResponse = useTutorStore((state) => state.last_response);
  const clearLastResponse = useTutorStore((state) => state.clearLastResponse);
  const recordResponse = useTutorStore((state) => state.recordResponse);

  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  const difficulty = useMemo(() => (examMode === "jee" ? "Adaptive JEE" : "CBSE practice"), [examMode]);
  const theme = useMemo(
    () =>
      examMode === "jee"
        ? { page: "bg-orange-50", card: "border-orange-200", chip: "bg-orange-100 text-orange-800", button: "bg-orange-600 hover:bg-orange-700" }
        : { page: "bg-blue-50", card: "border-blue-200", chip: "bg-blue-100 text-blue-800", button: "bg-blue-600 hover:bg-blue-700" },
    [examMode],
  );
  const practiceAllowed = examMode === "cbse" || canUseFeature(plan, "jee_practice");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || loading) return;

    setLoading(true);
    setError(null);
    clearLastResponse();

    try {
      const response = await sendAnswer({
        session_id: sessionId,
        mode: "practice",
        input: {
          question: currentQuestion,
          answer,
        },
        context: {
          exam: examMode,
        },
      });

      recordResponse(response);
      setAnswer("");
      setSeconds(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit answer");
    } finally {
      setLoading(false);
    }
  }

  function useSimilarQuestion() {
    if (!lastResponse?.next_question) return;
    const parts = lastResponse.next_question.split("\n").map((part) => part.trim()).filter(Boolean);
    setCurrentQuestion(parts[parts.length - 1] || currentQuestion);
    setAnswer("");
    setSeconds(0);
  }

  return (
    <main className={`min-h-[calc(100vh-4rem)] ${theme.page}`}>
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px]">
      {!practiceAllowed && (
        <div className="lg:col-span-2">
          <UpgradeNotice
            title="JEE adaptive practice is included in JEE Lite"
            description="Free practice is available for CBSE. Switch plans to unlock JEE adaptive questions, patterns, and timed practice."
            recommendedPlan="jee_lite"
          />
        </div>
      )}
      {practiceAllowed && (
        <>
      <section className="space-y-5">
        {currentConcept && (
          <div className={`rounded-2xl border ${theme.card} bg-white p-4 shadow-md`}>
            <p className="text-sm font-semibold text-slate-950">From Tutor Session</p>
            <p className="mt-1 text-sm text-slate-600">Now try a question from {currentConcept}.</p>
          </div>
        )}
        <div className={`rounded-2xl border ${theme.card} bg-white p-5 shadow-md transition`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-500">Topic</p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-950">Quadratic Equations</h1>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className={`rounded-xl px-3 py-2 font-medium ${theme.chip}`}>{difficulty}</span>
              <button
                type="button"
                onClick={() => setSeconds((value) => value + 1)}
                className="rounded-xl border border-slate-200 px-3 py-2 font-medium text-slate-700"
              >
                Timer {seconds}s
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-medium text-slate-500">Question</p>
            <p className="mt-3 text-xl font-semibold text-slate-950">{currentQuestion}</p>
          </div>

          <form onSubmit={onSubmit} className="mt-5 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Your answer</span>
              <input
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Example: -2,2"
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-slate-950 outline-none ring-slate-900 transition focus:ring-2"
              />
            </label>

            {error && <p className="text-sm text-rose-600">{error}</p>}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={loading || !answer.trim()}
                className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition disabled:cursor-not-allowed disabled:bg-slate-300 ${theme.button}`}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    Checking...
                  </span>
                ) : (
                  "Submit"
                )}
              </button>
              <button
                type="button"
                onClick={useSimilarQuestion}
                disabled={!lastResponse?.next_question}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
              >
                Try Similar Question
              </button>
              <button
                type="button"
                onClick={() => document.getElementById("practice-response")?.scrollIntoView({ behavior: "smooth" })}
                disabled={!lastResponse}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
              >
                View Explanation
              </button>
            </div>
          </form>
        </div>
      </section>

      <aside id="practice-response">
        <ResponsePanel response={lastResponse} />
      </aside>
        </>
      )}
    </div>
    </main>
  );
}
