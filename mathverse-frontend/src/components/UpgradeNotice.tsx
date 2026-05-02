"use client";

import { planLabels, type PlanKey, useTutorStore } from "../store/useTutorStore";

type Props = {
  title: string;
  description: string;
  recommendedPlan: PlanKey;
};

export function UpgradeNotice({ title, description, recommendedPlan }: Props) {
  const setPlan = useTutorStore((state) => state.setPlan);

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
      <p className="text-sm font-semibold uppercase text-amber-700">Plan feature</p>
      <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-700">{description}</p>
      <button
        type="button"
        onClick={() => setPlan(recommendedPlan)}
        className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800"
      >
        Switch to {planLabels[recommendedPlan]}
      </button>
    </div>
  );
}
