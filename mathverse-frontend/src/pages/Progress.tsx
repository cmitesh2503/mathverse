"use client";

import { useEffect, useMemo, useState } from "react";
import { StatCard } from "../components/StatCard";
import { getAttemptHistory, type AttemptRecord } from "../services/api";
import { useTutorStore } from "../store/useTutorStore";

export default function Progress() {
  const sessionId = useTutorStore((state) => state.session_id);
  const stats = useTutorStore((state) => state.stats);
  const [attempts, setAttempts] = useState<AttemptRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadAttempts() {
      try {
        const history = await getAttemptHistory(sessionId);
        if (!cancelled) {
          setAttempts(history);
          setHistoryError(null);
        }
      } catch {
        if (!cancelled) {
          setHistoryError("Saved attempt history is unavailable. Showing local session data.");
        }
      }
    }

    void loadAttempts();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const accuracy = stats.total ? Math.round((stats.correct / stats.total) * 100) : 0;
  const savedStats = useMemo(() => {
    const total = attempts.filter((attempt) => attempt.correct !== null && attempt.correct !== undefined).length;
    const correct = attempts.filter((attempt) => attempt.correct === true).length;
    const byMistake: Record<string, number> = {};
    const byTopic: Record<string, number> = {};
    const byPattern: Record<string, number> = {};

    attempts.forEach((attempt) => {
      if (attempt.mistake_type) {
        byMistake[attempt.mistake_type] = (byMistake[attempt.mistake_type] || 0) + 1;
      }
      if (attempt.correct === false && attempt.topic) {
        byTopic[attempt.topic] = (byTopic[attempt.topic] || 0) + 1;
      }
      if (attempt.correct === false && attempt.pattern) {
        byPattern[attempt.pattern] = (byPattern[attempt.pattern] || 0) + 1;
      }
    });

    return { total, correct, wrong: total - correct, byMistake, byTopic, byPattern };
  }, [attempts]);

  const effective = savedStats.total > stats.total ? savedStats : {
    total: stats.total,
    correct: stats.correct,
    wrong: stats.wrong,
    byMistake: stats.byMistake,
    byTopic: stats.byTopic,
    byPattern: stats.byPattern,
  };
  const effectiveAccuracy = effective.total ? Math.round((effective.correct / effective.total) * 100) : accuracy;
  const mistakes = Object.entries(effective.byMistake);
  const topics = Object.entries(effective.byTopic);
  const patterns = Object.entries(effective.byPattern);
  const predictedScore = Math.min(300, Math.round(effectiveAccuracy * 3));
  const sevenDayPlan = [
    "Day 1: Relearn the weakest concept using board examples.",
    "Day 2: Solve 20 easy questions without timer.",
    "Day 3: Fix the top mistake type with step-by-step review.",
    "Day 4: Attempt 20 medium questions with explanations.",
    "Day 5: Run a 30-minute timed mixed practice set.",
    "Day 6: Revise formulas, shortcuts, and saved notes.",
    "Day 7: Take a timed test and compare accuracy.",
  ];

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Accuracy" value={`${effectiveAccuracy}%`} />
        <StatCard label="Answered" value={`${effective.total}`} />
        <StatCard label="Correct" value={`${effective.correct}`} />
        <StatCard label="Wrong" value={`${effective.wrong}`} />
      </section>

      {historyError && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{historyError}</div>}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">Accuracy chart</h2>
          <div className="mt-4 h-4 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-emerald-500" style={{ width: `${effectiveAccuracy}%` }} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">Mistake types breakdown</h2>
          <div className="mt-4 space-y-3">
            {mistakes.length ? (
              mistakes.map(([type, count]) => (
                <div key={type} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                  <span>{type}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No mistakes recorded yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Score Prediction</h2>
          <p className="mt-4 text-4xl font-semibold text-slate-950">{predictedScore}</p>
          <p className="mt-2 text-sm text-slate-500">Estimated out of 300 from current accuracy. This becomes stronger as more timed attempts are logged.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">7-Day Improvement Plan</h2>
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {sevenDayPlan.map((item) => (
              <div key={item} className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Weak Topics</h2>
          <div className="mt-4 space-y-3">
            {topics.length ? (
              topics.map(([topic, count]) => (
                <div key={topic} className="flex items-center justify-between rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-800">
                  <span>{topic}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak topics recorded yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Weak Areas</h2>
          <div className="mt-4 space-y-3">
            {mistakes.length ? (
              mistakes.map(([type, count]) => (
                <div key={type} className="flex items-center justify-between rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  <span>{type.replace(/_/g, " ")}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak areas recorded yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">JEE Patterns to Improve</h2>
          <div className="mt-4 space-y-3">
            {patterns.length ? (
              patterns.map(([pattern, count]) => (
                <div key={pattern} className="flex items-center justify-between rounded-xl bg-orange-50 px-3 py-2 text-sm text-orange-800">
                  <span>{pattern}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak JEE patterns recorded yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
        <h2 className="font-semibold text-slate-950">📘 Concepts Learned</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {stats.conceptsLearned.length ? (
            stats.conceptsLearned.map((concept) => (
              <span key={concept} className="rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-800">
                {concept}
              </span>
            ))
          ) : (
            <p className="text-sm text-slate-500">Start a Tutor session to add concepts here.</p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-950">Recent performance</h2>
        <div className="mt-4 space-y-2">
          {stats.recent.map((response, index) => (
            <div key={index} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {response.correct ? "Correct" : "Incorrect"} {response.mistake_type ? `- ${response.mistake_type}` : ""}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
