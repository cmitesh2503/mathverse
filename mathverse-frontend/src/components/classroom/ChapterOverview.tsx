import type { ChapterLesson, StudentLevel } from "../../services/lessonTimeline";

type Props = {
  chapter: ChapterLesson;
  chapterProgress: number;
  studentLevel: StudentLevel;
};

const levelLabel: Record<StudentLevel, string> = {
  foundation: "Foundation pace",
  standard: "Standard pace",
  advanced: "Challenge pace",
};

export function ChapterOverview({ chapter, chapterProgress, studentLevel }: Props) {
  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Chapter overview</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-normal text-slate-950 sm:text-3xl">{chapter.title}</h1>
          <p className="mt-3 max-w-4xl text-base leading-7 text-slate-700">{chapter.overview.about}</p>
        </div>
        <div className="min-w-[190px] rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Chapter progress</p>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${chapterProgress}%` }} />
          </div>
          <p className="mt-2 text-sm font-semibold text-slate-800">{chapterProgress}% complete</p>
          <p className="mt-1 text-xs text-slate-500">{levelLabel[studentLevel]}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-2xl border border-blue-100 bg-blue-50/80 p-4">
          <p className="text-sm font-semibold text-blue-950">Why it matters</p>
          <p className="mt-2 text-sm leading-6 text-blue-900">{chapter.overview.whyItMatters}</p>
        </div>
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-4">
          <p className="text-sm font-semibold text-emerald-950">Main concepts</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {chapter.overview.mainConcepts.map((concept) => (
              <span key={concept} className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-semibold text-emerald-900">
                {concept}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-amber-100 bg-amber-50/80 p-4">
          <p className="text-sm font-semibold text-amber-950">Real-world intuition</p>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-amber-900">
            {chapter.overview.realWorldExamples.slice(0, 2).map((example) => (
              <li key={example}>{example}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
