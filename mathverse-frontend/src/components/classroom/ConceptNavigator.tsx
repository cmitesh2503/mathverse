import type { LessonConcept } from "../../services/lessonTimeline";

type Props = {
  concepts: LessonConcept[];
  currentIndex: number;
  completedConceptIds: string[];
  onSelectConcept: (index: number) => void;
};

function conceptStatus(concept: LessonConcept, index: number, currentIndex: number, completedConceptIds: string[]) {
  if (index === currentIndex) return "Current";
  if (completedConceptIds.includes(concept.id) || index < currentIndex) return "Completed";
  return "Upcoming";
}

function statusClass(status: string) {
  if (status === "Completed") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "Current") return "border-blue-300 bg-blue-50 text-blue-900 ring-2 ring-blue-100";
  return "border-slate-200 bg-white text-slate-600";
}

export function ConceptNavigator({ concepts, currentIndex, completedConceptIds, onSelectConcept }: Props) {
  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Concepts</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">Lesson path</h2>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          {currentIndex + 1}/{concepts.length}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {concepts.map((concept, index) => {
          const status = conceptStatus(concept, index, currentIndex, completedConceptIds);
          return (
            <button
              key={concept.id}
              type="button"
              onClick={() => onSelectConcept(index)}
              className={`w-full rounded-2xl border p-3 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${statusClass(status)}`}
            >
              <div className="flex items-start gap-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white text-sm font-bold shadow-sm">{index + 1}</span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold">{concept.title}</span>
                  <span className="mt-1 block text-xs leading-5 opacity-80">{concept.summary}</span>
                  <span className="mt-2 inline-flex rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-semibold">{status}</span>
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
