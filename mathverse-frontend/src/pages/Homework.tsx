"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { PageKey } from "../App";
import { Whiteboard } from "../components/Whiteboard";
import { sendAnswer, type ClassResponse, type HomeworkHelpResponse, type HomeworkQuestion, type HomeworkResponse } from "../services/api";
import { useTutorStore } from "../store/useTutorStore";

type Props = {
  onNavigate: (page: PageKey) => void;
};

function questionText(question: HomeworkQuestion, index: number) {
  return question.prompt || question.question || `Question ${index + 1}`;
}

function formatWeakArea(area: string) {
  return area.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function shortText(text?: string | null) {
  if (!text) return "";
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean);
  return (sentences.length ? sentences.slice(0, 2).join(" ") : text).trim();
}

export default function Homework({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const topic = useTutorStore((state) => state.currentTopic);
  const homeworkQuestions = useTutorStore((state) => state.homeworkQuestions);
  const homeworkAnswers = useTutorStore((state) => state.homeworkAnswers);
  const homeworkResult = useTutorStore((state) => state.homeworkResult);
  const setHomeworkQuestions = useTutorStore((state) => state.setHomeworkQuestions);
  const setHomeworkAnswer = useTutorStore((state) => state.setHomeworkAnswer);
  const setHomeworkAnswers = useTutorStore((state) => state.setHomeworkAnswers);
  const setHomeworkResult = useTutorStore((state) => state.setHomeworkResult);
  const setCurrentTopic = useTutorStore((state) => state.setCurrentTopic);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setPendingClassResponse = useTutorStore((state) => state.setPendingClassResponse);

  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [helpingIndex, setHelpingIndex] = useState<number | null>(null);
  const [helpBoard, setHelpBoard] = useState<HomeworkHelpResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);

  const theme = useMemo(
    () =>
      examMode === "jee"
        ? {
            page: "bg-orange-50",
            border: "border-orange-200",
            chip: "bg-orange-100 text-orange-800",
            button: "bg-orange-600 hover:bg-orange-700",
            soft: "bg-orange-50 text-orange-900",
          }
        : {
            page: "bg-blue-50",
            border: "border-blue-200",
            chip: "bg-blue-100 text-blue-800",
            button: "bg-blue-600 hover:bg-blue-700",
            soft: "bg-blue-50 text-blue-900",
          },
    [examMode],
  );

  useEffect(() => {
    async function loadHomework() {
      setLoadingQuestions(true);
      setError(null);
      setHomeworkResult(null);

      try {
        const data = await sendAnswer<HomeworkResponse>({
          session_id: sessionId,
          mode: "homework",
          input: { topic },
          context: { exam: examMode },
        });

        setHomeworkQuestions(data.questions || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load homework");
      } finally {
        setLoadingQuestions(false);
      }
    }

    void loadHomework();
  }, [examMode, sessionId, setHomeworkQuestions, setHomeworkResult, topic]);

  async function submitHomework(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!homeworkQuestions.length || evaluating) return;

    setEvaluating(true);
    setError(null);

    try {
      const data = await sendAnswer<HomeworkResponse>({
        session_id: sessionId,
        mode: "homework",
        input: {
          topic,
          answers: homeworkAnswers,
        },
        context: { exam: examMode },
      });

      setHomeworkResult(data);
      if (data.next_class) {
        setPendingClassResponse(data.next_class);
      }
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to evaluate homework");
    } finally {
      setEvaluating(false);
    }
  }

  function retryHomework() {
    setHomeworkResult(null);
    setHelpBoard(null);
    setHomeworkAnswers(homeworkQuestions.map(() => ""));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function requestHomeworkHelp(index: number) {
    setHelpingIndex(index);
    setHelpBoard({
      type: "homework_help",
      explanation: "Opening the whiteboard solution...",
      question: homeworkQuestions[index],
      steps: [],
      whiteboard: {
        mode: "homework_help",
        title: topic || "Homework",
        subtitle: "Preparing step-by-step solution",
        problem: questionText(homeworkQuestions[index], index),
        chalk_lines: ["Loading solution steps..."],
      },
    });
    setError(null);

    try {
      const data = await sendAnswer<HomeworkHelpResponse>({
        session_id: sessionId,
        mode: "homework",
        input: {
          topic,
          action: "help",
          question_index: index,
          question_data: homeworkQuestions[index],
        },
        context: { exam: examMode },
      });
      setHomeworkAnswer(index, "__unable__");
      setHelpBoard(data);
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load homework help");
    } finally {
      setHelpingIndex(null);
    }
  }

  async function skipHomework() {
    if (skipping) return;

    setSkipping(true);
    setError(null);

    try {
      const data = await sendAnswer<ClassResponse>({
        session_id: sessionId,
        mode: "class",
        input: { action: "skip_homework" },
        context: { exam: examMode },
      });
      setHomeworkQuestions([]);
      setHomeworkAnswers([]);
      setHomeworkResult(null);
      setPendingClassResponse(data);
      onNavigate("class");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to skip homework");
    } finally {
      setSkipping(false);
    }
  }

  function continueLearning() {
    if (homeworkResult?.next_class) {
      const nextTopic = homeworkResult.next_topic || homeworkResult.next_class.topic || homeworkResult.next_class.chapter || homeworkResult.next_class.content?.chapter || topic;
      setCurrentTopic(nextTopic);
      setCurrentConcept(homeworkResult.next_concept || homeworkResult.next_class.concept || homeworkResult.next_class.content?.concept || null);
      setHomeworkQuestions([]);
      setHomeworkAnswers([]);
      setHomeworkResult(null);
      onNavigate("learn");
    }
  }

  const answeredCount = homeworkAnswers.filter((answer) => answer.trim()).length;
  const scoreMax = homeworkQuestions.length || 10;
  const canSubmit = homeworkQuestions.length > 0 && answeredCount > 0 && !evaluating && !loadingQuestions;

  return (
    <main className={`min-h-[calc(100vh-4rem)] ${theme.page}`}>
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-6 sm:px-6">
        <section className={`rounded-2xl border ${theme.border} bg-white p-5 shadow-md`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase text-slate-500">📚 Homework</p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-950">Homework: {topic || "Quadratics"}</h1>
            </div>
            <span className={`rounded-xl px-3 py-2 text-xs font-semibold uppercase ${theme.chip}`}>{examMode}</span>
          </div>
        </section>

        {error && <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-rose-700 shadow-md">{error}</div>}

        <form onSubmit={submitHomework} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-950">✏️ Solve the following</h2>
            <p className="text-sm font-medium text-slate-500">
              {answeredCount}/{homeworkQuestions.length} answered
            </p>
          </div>

          <div className="mt-5 space-y-4">
            {loadingQuestions ? (
              <div className="flex items-center gap-3 rounded-2xl bg-slate-50 p-5 text-sm font-medium text-slate-600">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
                Preparing homework...
              </div>
            ) : homeworkQuestions.length ? (
              homeworkQuestions.map((question, index) => {
                const solvedCleanly = homeworkResult && homeworkResult.weak_areas.length === 0;
                const emptyAfterSubmit = homeworkResult && !homeworkAnswers[index]?.trim();
                const inputState = solvedCleanly
                  ? "border-emerald-300 bg-emerald-50"
                  : emptyAfterSubmit
                    ? "border-rose-300 bg-rose-50"
                    : "border-slate-300 bg-white";

                return (
                  <label key={`${questionText(question, index)}-${index}`} className="block rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <span className="block text-base font-semibold leading-7 text-slate-950">
                      Q{index + 1}. {questionText(question, index)}
                    </span>
                    <input
                      value={homeworkAnswers[index] || ""}
                      onChange={(event) => setHomeworkAnswer(index, event.target.value)}
                      disabled={evaluating}
                      placeholder="Type your answer"
                      className={`mt-3 w-full rounded-xl border px-3 py-3 text-slate-950 outline-none transition focus:ring-2 focus:ring-slate-900 disabled:cursor-not-allowed disabled:text-slate-400 ${inputState}`}
                    />
                    <button
                      type="button"
                      onClick={() => requestHomeworkHelp(index)}
                      disabled={helpingIndex === index || evaluating}
                      className="mt-3 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:text-slate-300"
                    >
                      {helpingIndex === index ? "Opening help..." : "I can't solve this"}
                    </button>
                  </label>
                );
              })
            ) : (
              <div className="rounded-2xl bg-slate-50 p-5 text-sm text-slate-600">No homework questions found for this topic.</div>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className={`mt-5 rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-sm transition disabled:cursor-not-allowed disabled:bg-slate-300 ${theme.button}`}
          >
            {evaluating ? (
              <span className="inline-flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Evaluating...
              </span>
            ) : (
              "Submit Homework"
            )}
          </button>
          <button
            type="button"
            onClick={skipHomework}
            disabled={skipping || evaluating || loadingQuestions}
            className="ml-3 mt-5 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          >
            {skipping ? "Skipping..." : "Skip Homework"}
          </button>
        </form>

        {helpBoard && (
          <section ref={resultRef} className="rounded-2xl border border-blue-200 bg-white p-5 shadow-md">
            <div className="mb-4">
              <p className="text-sm font-semibold uppercase text-blue-700">Homework Help</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Step-by-step board solution</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{helpBoard.explanation}</p>
            </div>
            <Whiteboard steps={helpBoard.steps || []} whiteboard={helpBoard.whiteboard} visibleStepCount={helpBoard.steps?.length || 0} />
          </section>
        )}

        {homeworkResult && (
          <section ref={resultRef} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md transition">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-slate-950">📊 Your Result</h2>
              <div className={`rounded-xl px-4 py-2 text-sm font-semibold ${theme.soft}`}>
                Score: {homeworkResult.score ?? 0} / {scoreMax}
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="font-semibold text-slate-950">❌ Weak Areas</p>
                {homeworkResult.weak_areas.length ? (
                  <ul className="mt-3 space-y-2 text-sm text-slate-700">
                    {homeworkResult.weak_areas.map((area) => (
                      <li key={area}>- {formatWeakArea(area)}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-emerald-700">No major weak areas found.</p>
                )}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="font-semibold text-slate-950">🚀 Next Step</p>
                <p className="mt-3 text-sm leading-6 text-slate-700">{homeworkResult.next_recommendation}</p>
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="font-semibold text-slate-950">🧠 Explanation</p>
              <p className="mt-3 text-sm leading-6 text-slate-700">{shortText(homeworkResult.explanation) || "Review the weak areas and try again."}</p>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={retryHomework}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
              >
                Retry Homework
              </button>
              <button
                type="button"
                onClick={() => onNavigate("class")}
                className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition ${theme.button}`}
              >
                Continue Class
              </button>
              <button
                type="button"
                onClick={continueLearning}
                disabled={!homeworkResult.next_class}
                className={`rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition disabled:bg-slate-300 ${theme.button}`}
              >
                Continue Learning
              </button>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
