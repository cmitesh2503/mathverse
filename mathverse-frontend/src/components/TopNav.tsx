"use client";

import type { PageKey } from "../App";
import type { MathverseSession } from "../services/firestoreAuth";
import { planLabels, type PlanKey, useTutorStore } from "../store/useTutorStore";

const navItems: { key: PageKey; label: string }[] = [
  { key: "home", label: "Home" },
  { key: "class", label: "Class" },
  { key: "learn", label: "Learn" },
  { key: "practice", label: "Practice" },
  { key: "homework", label: "Homework" },
  { key: "solve", label: "Solve" },
  { key: "exam", label: "Exam" },
  { key: "progress", label: "Progress" },
  { key: "report", label: "Reports" },
  { key: "subscription", label: "Subscription" },
];

type Props = {
  active: PageKey;
  onNavigate: (page: PageKey) => void;
  session?: MathverseSession | null;
  onLogout?: () => void;
};

export function TopNav({ active, onNavigate, session, onLogout }: Props) {
  const examMode = useTutorStore((state) => state.exam_mode);
  const plan = useTutorStore((state) => state.plan);
  const setExamMode = useTutorStore((state) => state.setExamMode);
  const setPlan = useTutorStore((state) => state.setPlan);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() =>
              onNavigate(
                examMode === "jee"
                  ? "jee-home"
                  : "home"
              )
            }
            className="text-lg font-semibold text-slate-950"
          >
            {examMode === "jee"
              ? "MathVerse JEE"
              : "MathVerse CBSE"}
          </button>
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => onNavigate(item.key)}
                className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
                  active === item.key
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {session && (
            <div className="flex items-center gap-2">
              <span className="hidden max-w-32 truncate text-xs font-medium text-slate-600 sm:block lg:max-w-44">
                {session.fullName || session.email}
              </span>
              <button
                type="button"
                onClick={onLogout}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Logout
              </button>
            </div>
          )}

          <select
            value={plan}
            onChange={(event) => setPlan(event.target.value as PlanKey)}
            className="hidden rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm outline-none sm:block"
            aria-label="Plan"
          >
            {(Object.keys(planLabels) as PlanKey[]).map((key) => (
              <option key={key} value={key}>
                {planLabels[key]}
              </option>
            ))}
          </select>

          <div className="flex rounded-xl border border-slate-200 bg-slate-50 p-1 shadow-sm">
          {(["cbse", "jee"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => {
                setExamMode(mode);

                if (mode === "jee") {
                  onNavigate("jee-home");
                } else {
                  onNavigate("home");
                }
              }}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold uppercase transition ${
                examMode === mode
                  ? mode === "jee"
                    ? "bg-orange-100 text-orange-800 shadow-sm"
                    : "bg-blue-100 text-blue-800 shadow-sm"
                  : "text-slate-500"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
        </div>
      </div>
    </header>
  );
}
