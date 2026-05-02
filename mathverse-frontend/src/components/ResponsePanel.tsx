import type { TutorResponse } from "../services/api";

type Props = {
  response: TutorResponse | null;
};

export function ResponsePanel({ response }: Props) {
  if (!response) return null;

  const explanation = Array.isArray(response.explanation)
    ? response.explanation.join(" ")
    : response.explanation;

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            response.correct ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
          }`}
        >
          {response.correct ? "✅ Correct" : "❌ Incorrect"}
        </span>
        {response.mistake_type && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
            {response.mistake_type}
          </span>
        )}
      </div>

      {response.hint && (
        <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">
          <p className="font-semibold">💡 Hint</p>
          <p className="mt-1">{response.hint}</p>
        </div>
      )}

      {explanation && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950">
          <p className="font-semibold">📘 Explanation</p>
          <p className="mt-1 leading-6">{explanation}</p>
        </div>
      )}

      {!!response.steps?.length && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-950">🧠 Steps</p>
          <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
            {response.steps.map((step, index) => (
              <li key={`${step}-${index}`}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {response.shortcut && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">⚡ Shortcut</p>
          <p className="mt-1">{response.shortcut}</p>
        </div>
      )}

      {response.speed_hint && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
          <p className="font-semibold">Speed hint</p>
          <p className="mt-1">{response.speed_hint}</p>
        </div>
      )}

      {response.adaptive_hint && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 text-sm text-violet-900">
          <p className="font-semibold">🎯 Adaptive Hint</p>
          <p className="mt-1">{response.adaptive_hint}</p>
        </div>
      )}
    </section>
  );
}
