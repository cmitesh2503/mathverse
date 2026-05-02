"use client";

import { StatCard } from "../components/StatCard";
import { planLabels, type PlanKey, useTutorStore } from "../store/useTutorStore";
import type { PageKey } from "../App";

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function Home({ onNavigate }: Props) {
  const stats = useTutorStore((state) => state.stats);
  const plan = useTutorStore((state) => state.plan);
  const setPlan = useTutorStore((state) => state.setPlan);
  const accuracy = stats.total ? Math.round((stats.correct / stats.total) * 100) : 0;
  const weakTopic = Object.entries(stats.byMistake).sort((a, b) => b[1] - a[1])[0]?.[0] || "None yet";
  const plans: Array<{ key: PlanKey; features: string[]; action: PageKey }> = [
    { key: "free", features: ["Basic CBSE practice", "Solver access", "Local progress"], action: "practice" },
    { key: "cbse_pro", features: ["Full CBSE syllabus", "Whiteboard class", "Voice and notes"], action: "class" },
    { key: "jee_lite", features: ["JEE adaptive practice", "Timed tests", "Pattern drills"], action: "practice" },
    { key: "jee_pro", features: ["Full JEE engine", "Analytics", "Speed mode and prediction"], action: "progress" },
  ];

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Adaptive math tutor</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-950">Practice with targeted feedback</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Switch between CBSE learning and JEE speed practice from the top bar.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate("practice")}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800"
          >
            Start Practice
          </button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <StatCard label="Accuracy" value={`${accuracy}%`} detail={`${stats.correct}/${stats.total} correct`} />
        <StatCard label="Weak Topic" value={weakTopic} detail="Based on recent mistakes" />
        <StatCard label="Strong Topic" value={stats.correct ? "Quadratics" : "Not enough data"} detail="Updates with practice" />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <button
          type="button"
          onClick={() => onNavigate("homework")}
          className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-md hover:border-slate-300"
        >
          <p className="font-semibold text-slate-950">📚 Homework Pending</p>
          <p className="mt-2 text-sm text-slate-500">Topic: Quadratics</p>
          <span className="mt-4 inline-flex rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700">
            Start Homework
          </span>
        </button>
        <button
          type="button"
          onClick={() => onNavigate("solve")}
          className="rounded-lg border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-slate-300"
        >
          <p className="font-semibold text-slate-950">Solve Question</p>
          <p className="mt-1 text-sm text-slate-500">Use text, image, or voice input placeholders.</p>
        </button>
        <button
          type="button"
          onClick={() => onNavigate("exam")}
          className="rounded-lg border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-slate-300"
        >
          <p className="font-semibold text-slate-950">Take Test</p>
          <p className="mt-1 text-sm text-slate-500">Run a JEE-style adaptive exam session.</p>
        </button>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase text-slate-500">Plans</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">Choose the learning engine</h2>
          </div>
          <span className="rounded-xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
            Active: {planLabels[plan]}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-4">
          {plans.map((item) => {
            const active = item.key === plan;
            return (
              <div
                key={item.key}
                className={`rounded-2xl border p-4 ${
                  active ? "border-slate-900 bg-slate-50" : "border-slate-200 bg-white"
                }`}
              >
                <h3 className="font-semibold text-slate-950">{planLabels[item.key]}</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-600">
                  {item.features.map((feature) => (
                    <li key={feature}>- {feature}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={() => {
                    setPlan(item.key);
                    onNavigate(item.action);
                  }}
                  className={`mt-4 w-full rounded-xl px-3 py-2 text-sm font-semibold ${
                    active ? "bg-slate-900 text-white" : "border border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {active ? "Continue" : "Switch"}
                </button>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
