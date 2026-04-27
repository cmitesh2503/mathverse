"use client";

import { useEffect, useState } from "react";

type HomeworkQuestion = {
  question: string;
  type?: string;
  difficulty?: string;
};

type HomeworkRecord = {
  class?: number;
  chapter?: string;
  topic?: string;
  title?: string;
  questions?: HomeworkQuestion[];
};

type HomeworkTabProps = {
  apiBase?: string;
  studentId: string;
  inlineHomework?: string[];
  topicTitle?: string | null;
  chapterLabel?: string;
};

export default function HomeworkTab({
  apiBase,
  studentId,
  inlineHomework = [],
  topicTitle,
  chapterLabel,
}: HomeworkTabProps) {
  const [homeworks, setHomeworks] = useState<HomeworkRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId || !apiBase) {
      return;
    }

    let cancelled = false;

    const loadHomework = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${apiBase}/homework/${encodeURIComponent(studentId)}`);
        if (!response.ok) {
          throw new Error("Could not load saved homework.");
        }

        const payload = (await response.json()) as HomeworkRecord[];
        if (!cancelled) {
          setHomeworks(Array.isArray(payload) ? payload : []);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Could not load saved homework."
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadHomework();

    return () => {
      cancelled = true;
    };
  }, [apiBase, studentId]);

  return (
    <div className="space-y-4">
      <div className="rounded-[1.4rem] border border-emerald-200 bg-emerald-50 px-4 py-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-700">
          Current Lesson Homework
        </div>
        <div className="mt-2 text-sm text-slate-600">
          {chapterLabel || "Current chapter"}
          {topicTitle ? ` - ${topicTitle}` : ""}
        </div>
        <div className="mt-3 space-y-2">
          {inlineHomework.length > 0 ? (
            inlineHomework.map((task, index) => (
              <div
                key={`${task}-${index}`}
                className="rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm text-slate-700"
              >
                {index + 1}. {task}
              </div>
            ))
          ) : (
            <div className="rounded-2xl border border-dashed border-emerald-200 bg-white/70 px-4 py-4 text-sm text-slate-500">
              Ava will push remaining chapter work here after the in-class board explanation.
            </div>
          )}
        </div>
      </div>

      <div className="rounded-[1.4rem] border border-slate-200 bg-white px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-700">
              Saved Homework Agent Output
            </div>
            <div className="mt-1 text-sm text-slate-500">
              Previously generated homework sets for this learner.
            </div>
          </div>
          {isLoading && (
            <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              Loading...
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </div>
        )}

        <div className="mt-4 space-y-4">
          {homeworks.length === 0 && !isLoading && !error && (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-4 text-sm text-slate-500">
              No saved homework has been generated yet for this student.
            </div>
          )}

          {homeworks.map((homework, index) => (
            <div
              key={`${homework.title ?? "homework"}-${index}`}
              className="rounded-[1.25rem] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f7f5f0_100%)] px-4 py-4"
            >
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                Class {homework.class ?? "-"} - {homework.chapter ?? "Homework set"}
              </div>
              <div className="mt-2 text-lg font-semibold text-slate-900">
                {homework.title || `${homework.topic || "Mathematics"} Homework`}
              </div>
              {homework.questions?.length ? (
                <div className="mt-4 space-y-2">
                  {homework.questions.map((question, questionIndex) => (
                    <div
                      key={`${question.question}-${questionIndex}`}
                      className="rounded-2xl border border-slate-100 bg-white px-4 py-3 text-sm text-slate-700"
                    >
                      <div>
                        {questionIndex + 1}. {question.question}
                      </div>
                      {(question.type || question.difficulty) && (
                        <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                          {[question.type, question.difficulty].filter(Boolean).join(" - ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-dashed border-slate-200 px-4 py-4 text-sm text-slate-500">
                  This homework set did not include structured questions.
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
