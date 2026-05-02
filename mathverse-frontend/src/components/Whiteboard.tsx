"use client";

import { useEffect, useMemo, useState } from "react";
import type { WhiteboardState } from "../services/api";

type Props = {
  steps: string[];
  whiteboard?: WhiteboardState | null;
  delayMs?: number;
  visibleStepCount?: number;
};

export function renderStepWithVoice(step: string, delay: number, onRender: () => void) {
  return window.setTimeout(onRender, Math.max(0, delay + step.length * 12));
}

export function addStep(steps: string[], step: string) {
  return step && !steps.includes(step) ? [...steps, step] : steps;
}

export function Whiteboard({ steps, whiteboard, delayMs = 950, visibleStepCount }: Props) {
  const [visibleCount, setVisibleCount] = useState(0);
  const boardSteps = useMemo(
    () =>
      steps.length
        ? steps
        : [
            ...(whiteboard?.solution_steps || []),
            ...(whiteboard?.equations || []),
            ...(whiteboard?.chalk_lines || []),
          ],
    [steps, whiteboard],
  );

  useEffect(() => {
    if (visibleStepCount !== undefined) return;

    setVisibleCount(0);
    if (!boardSteps.length) return;

    const timers = boardSteps.map((step, index) =>
      renderStepWithVoice(step, delayMs * index, () => {
        setVisibleCount((count) => Math.max(count, index + 1));
      }),
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [boardSteps, delayMs, visibleStepCount]);

  const renderedCount = steps.length ? steps.length : visibleStepCount ?? visibleCount;
  const modeLabel = whiteboard?.mode ? whiteboard.mode.replace(/_/g, " ") : "Live writing";

  return (
    <div className="rounded-2xl bg-white p-5 shadow-lg ring-1 ring-slate-200">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{whiteboard?.title || "Whiteboard"}</h2>
          {whiteboard?.subtitle && <p className="mt-1 text-sm text-slate-500">{whiteboard.subtitle}</p>}
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold capitalize text-slate-600">{modeLabel}</span>
      </div>

      <div className="mt-5 min-h-72 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-5">
        {whiteboard?.problem && (
          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 font-mono text-base font-semibold leading-7 text-blue-950">
            {whiteboard.problem}
          </div>
        )}

        {boardSteps.length ? (
          boardSteps.slice(0, renderedCount).map((step, index) => (
            <div
              key={`${step}-${index}`}
              className="animate-[fadeIn_0.35s_ease-out] rounded-xl bg-white px-4 py-3 font-mono text-lg font-semibold leading-8 text-slate-950 opacity-100 shadow-sm transition duration-500"
            >
              Step {index + 1}: {step}
            </div>
          ))
        ) : (
          <div className="rounded-xl bg-white px-4 py-3 text-sm font-medium text-slate-500 shadow-sm">Waiting for steps...</div>
        )}

        {whiteboard?.answer && renderedCount >= boardSteps.length && (
          <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 font-mono text-base font-semibold text-emerald-950">
            Answer: {whiteboard.answer}
          </div>
        )}
      </div>
    </div>
  );
}
