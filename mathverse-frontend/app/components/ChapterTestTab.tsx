"use client";

import { useEffect, useMemo, useState } from "react";
import type { ChapterTest, ChapterTestResult } from "../types/chapter-test";

type ChapterTestTabProps = {
  apiBase?: string;
  sessionId?: string | null;
  lessonStage?: string | null;
  chapterLabel?: string;
  topicTitle?: string | null;
  enabled?: boolean;
};

type ChapterTestResponse = {
  chapter_test: ChapterTest;
  latest_result?: ChapterTestResult | null;
};

const verdictTone = (verdict: string) => {
  const normalized = verdict.toLowerCase();
  if (normalized.includes("excellent")) {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (normalized.includes("good")) {
    return "border-sky-200 bg-sky-50 text-sky-900";
  }
  return "border-amber-200 bg-amber-50 text-amber-900";
};

export default function ChapterTestTab({
  apiBase,
  sessionId,
  lessonStage,
  chapterLabel,
  topicTitle,
  enabled = false,
}: ChapterTestTabProps) {
  const [chapterTest, setChapterTest] = useState<ChapterTest | null>(null);
  const [result, setResult] = useState<ChapterTestResult | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canAutoPrepare = lessonStage === "WRAP";

  const loadChapterTest = async (refresh = false) => {
    if (!apiBase || !sessionId) {
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const suffix = refresh ? "?refresh=true" : "";
      const response = await fetch(
        `${apiBase}/evaluation/chapter-test/${encodeURIComponent(sessionId)}${suffix}`
      );
      if (!response.ok) {
        throw new Error("Could not load the chapter test.");
      }

      const payload = (await response.json()) as ChapterTestResponse;
      setChapterTest(payload.chapter_test);
      setResult(payload.latest_result ?? null);
      setAnswers((current) => {
        const next: Record<string, string> = {};
        for (const question of payload.chapter_test.questions) {
          next[question.id] = current[question.id] ?? "";
        }
        return next;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load the chapter test.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!enabled || !sessionId || !apiBase) {
      return;
    }
    void loadChapterTest();
  }, [apiBase, enabled, sessionId]);

  useEffect(() => {
    if (!enabled || !canAutoPrepare || !sessionId || !apiBase || chapterTest) {
      return;
    }
    void loadChapterTest();
  }, [apiBase, canAutoPrepare, chapterTest, enabled, sessionId]);

  useEffect(() => {
    setChapterTest(null);
    setResult(null);
    setAnswers({});
    setError(null);
  }, [sessionId]);

  const unansweredCount = useMemo(() => {
    if (!chapterTest) {
      return 0;
    }
    return chapterTest.questions.filter((question) => !answers[question.id]?.trim()).length;
  }, [answers, chapterTest]);

  const submitChapterTest = async () => {
    if (!apiBase || !sessionId || !chapterTest) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(
        `${apiBase}/evaluation/chapter-test/${encodeURIComponent(sessionId)}/submit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ answers }),
        }
      );

      if (!response.ok) {
        throw new Error("Could not submit the chapter test.");
      }

      const payload = (await response.json()) as { result: ChapterTestResult };
      setResult(payload.result);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Could not submit the chapter test."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-[1.4rem] border border-sky-200 bg-sky-50 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-700">
              Assessment Agent
            </div>
            <div className="mt-2 text-lg font-semibold text-slate-900">
              {chapterLabel || "Chapter test"}
              {topicTitle ? ` - ${topicTitle}` : ""}
            </div>
            <div className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              This agent prepares a chapter-end evaluation and checks the submitted answers
              separately from the teaching flow.
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600">
              {canAutoPrepare ? "Auto-ready at chapter wrap" : "Manual prep available"}
            </div>
            <button
              onClick={() => void loadChapterTest(true)}
              disabled={!apiBase || !sessionId || isLoading}
              className={`rounded-full px-4 py-2 text-xs font-semibold ${
                !apiBase || !sessionId || isLoading
                  ? "cursor-not-allowed bg-slate-200 text-slate-500"
                  : "bg-slate-900 text-white transition hover:bg-slate-700"
              }`}
            >
              {isLoading ? "Preparing..." : chapterTest ? "Regenerate Test" : "Prepare Test"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      )}

      {!chapterTest && !isLoading && (
        <div className="rounded-[1.4rem] border border-dashed border-slate-200 bg-white px-4 py-5 text-sm text-slate-500">
          {canAutoPrepare
            ? "The chapter has ended. Use Prepare Test if the evaluation sheet is not visible yet."
            : "The assessment agent can generate a chapter test now, and it will also be ready automatically when the chapter wrap stage is reached."}
        </div>
      )}

      {chapterTest && (
        <div className="rounded-[1.4rem] border border-slate-200 bg-white px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                {chapterTest.title}
              </div>
              <div className="mt-2 text-sm leading-6 text-slate-600">
                {chapterTest.instructions}
              </div>
            </div>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              {chapterTest.questions.length} questions
            </div>
          </div>

          <div className="mt-4 space-y-4">
            {chapterTest.questions.map((question, index) => (
              <div
                key={question.id}
                className="rounded-[1.2rem] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#faf8f3_100%)] px-4 py-4"
              >
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">
                  Question {index + 1}
                  {question.concept_title ? ` - ${question.concept_title}` : ""}
                </div>
                <div className="mt-2 text-sm leading-6 text-slate-800">{question.prompt}</div>
                <div className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-400">
                  {question.answer_format}
                </div>

                {question.kind === "short" ? (
                  <textarea
                    value={answers[question.id] ?? ""}
                    onChange={(event) =>
                      setAnswers((current) => ({
                        ...current,
                        [question.id]: event.target.value,
                      }))
                    }
                    rows={4}
                    className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-amber-300"
                    placeholder="Write your answer here..."
                  />
                ) : (
                  <input
                    value={answers[question.id] ?? ""}
                    onChange={(event) =>
                      setAnswers((current) => ({
                        ...current,
                        [question.id]: event.target.value,
                      }))
                    }
                    className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-amber-300"
                    placeholder="Type your answer..."
                  />
                )}
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-slate-500">
              {unansweredCount > 0
                ? `${unansweredCount} question${unansweredCount === 1 ? "" : "s"} still unanswered`
                : "All questions are filled"}
            </div>
            <button
              onClick={() => void submitChapterTest()}
              disabled={isSubmitting || !chapterTest}
              className={`rounded-full px-5 py-2 text-sm font-semibold ${
                isSubmitting || !chapterTest
                  ? "cursor-not-allowed bg-slate-200 text-slate-500"
                  : "bg-amber-600 text-white transition hover:bg-amber-700"
              }`}
            >
              {isSubmitting ? "Evaluating..." : "Submit For Evaluation"}
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="rounded-[1.4rem] border border-slate-200 bg-white px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                Evaluation Result
              </div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">
                {result.score} / {result.max_score}
              </div>
            </div>
            <div
              className={`rounded-full border px-4 py-2 text-sm font-semibold ${verdictTone(
                result.verdict
              )}`}
            >
              {result.verdict} - {result.percentage}%
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {result.feedback.map((item) => (
              <div
                key={item.question_id}
                className={`rounded-2xl border px-4 py-4 ${
                  item.correct
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-amber-200 bg-amber-50"
                }`}
              >
                <div className="text-sm font-semibold text-slate-900">{item.prompt}</div>
                <div className="mt-2 text-sm text-slate-700">
                  Your answer: {item.submitted || "No answer submitted"}
                </div>
                <div className="mt-1 text-sm text-slate-700">Expected: {item.expected}</div>
                <div className="mt-2 text-sm text-slate-700">{item.feedback}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
