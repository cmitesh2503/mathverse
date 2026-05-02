"use client";

import { useMemo, useState } from "react";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { sendAnswer } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

const questions = [
  "x^2 - 9 = 0",
  "x^2 - 5x + 6 = 0",
  "2x^2 - 10x + 12 = 0",
];

export default function Exam() {
  const sessionId = useTutorStore((state) => state.session_id);
  const plan = useTutorStore((state) => state.plan);
  const stats = useTutorStore((state) => state.stats);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState(0);

  const accuracy = useMemo(() => {
    return questions.length ? Math.round((score / questions.length) * 100) : 0;
  }, [score]);
  const examAllowed = canUseFeature(plan, "exam");

  async function submitExam() {
    setLoading(true);
    let correct = 0;
    try {
      for (let i = 0; i < questions.length; i += 1) {
        const response = await sendAnswer({
          session_id: sessionId,
          mode: "practice",
          input: {
            question: questions[i],
            answer: answers[i] || "",
          },
          context: { exam: "jee" },
        });
        if (response.correct) correct += 1;
      }
      setScore(correct);
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      {!examAllowed && (
        <UpgradeNotice
          title="Timed exam mode is included in JEE Lite"
          description="Unlock timed tests, score tracking, and rank-estimation foundations by switching to JEE Lite or JEE Pro."
          recommendedPlan="jee_lite"
        />
      )}
      {examAllowed && (
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-500">JEE mode</p>
            <h1 className="text-2xl font-semibold text-slate-950">Adaptive Exam</h1>
          </div>
          <div className="rounded-md bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">Timer 00:00</div>
        </div>

        {!submitted ? (
          <div className="mt-6 space-y-5">
            <div className="text-sm font-medium text-slate-500">
              Question {index + 1} of {questions.length}
            </div>
            <div className="rounded-lg bg-slate-50 p-5 text-xl font-semibold text-slate-950">{questions[index]}</div>
            <input
              value={answers[index] || ""}
              onChange={(event) => setAnswers((current) => ({ ...current, [index]: event.target.value }))}
              placeholder="Answer"
              className="w-full rounded-md border border-slate-300 px-3 py-3 outline-none focus:ring-2 focus:ring-slate-900"
            />
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setIndex((value) => Math.max(0, value - 1))}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
              >
                Previous
              </button>
              <button
                onClick={() => setIndex((value) => Math.min(questions.length - 1, value + 1))}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
              >
                Next
              </button>
              <button
                onClick={submitExam}
                disabled={loading}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
              >
                {loading ? "Submitting..." : "Submit Exam"}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Score</p>
              <p className="mt-2 text-2xl font-semibold">{score}/{questions.length}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Accuracy</p>
              <p className="mt-2 text-2xl font-semibold">{accuracy}%</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Weak patterns</p>
              <p className="mt-2 text-sm font-semibold">{Object.keys(stats.byMistake)[0] || "None"}</p>
            </div>
          </div>
        )}
      </section>
      )}
    </main>
  );
}
