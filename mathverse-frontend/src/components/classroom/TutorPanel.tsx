import type { FormEvent } from "react";
import { TutorAvatar } from "../TutorAvatar";

export type ClassroomDiscussionTurn = {
  id: string;
  role: "student" | "tutor";
  content: string;
};

type Props = {
  tutorLabel: string;
  conceptTitle: string;
  currentStepLabel: string;
  currentSpeech: string;
  isSpeaking: boolean;
  isPaused: boolean;
  loadingAnswer: boolean;
  questionText: string;
  discussionTurns: ClassroomDiscussionTurn[];
  confusionDetected: boolean;
  onQuestionChange: (value: string) => void;
  onQuestionSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUsePrompt: (prompt: string) => void;
};

const quickPrompts = ["Please explain that differently", "Why does this step work?", "Give me one easier example"];

export function TutorPanel({
  tutorLabel,
  conceptTitle,
  currentStepLabel,
  currentSpeech,
  isSpeaking,
  isPaused,
  loadingAnswer,
  questionText,
  discussionTurns,
  confusionDetected,
  onQuestionChange,
  onQuestionSubmit,
  onUsePrompt,
}: Props) {
  const status = loadingAnswer ? "Thinking through your question" : isPaused ? "Paused" : isSpeaking ? "Explaining now" : "Ready";

  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <TutorAvatar label={tutorLabel} speaking={isSpeaking} text={status} />

      <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Current concept</p>
        <h2 className="mt-2 text-lg font-semibold leading-7 text-slate-950">{conceptTitle}</h2>
        <p className="mt-2 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">{currentStepLabel}</p>
      </div>

      <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/80 p-4">
        <p className="text-sm font-semibold text-blue-950">Tutor explanation</p>
        <p className="mt-2 min-h-24 text-sm leading-6 text-blue-950">
          {currentSpeech || "Press play when you are ready. The tutor will introduce the chapter and write on the board in sync."}
        </p>
      </div>

      {confusionDetected && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          The tutor detected confusion and switched to a smaller-step explanation.
        </div>
      )}

      <form onSubmit={onQuestionSubmit} className="mt-4 rounded-2xl border border-slate-200 p-4">
        <label className="block">
          <span className="text-sm font-semibold text-slate-900">Ask a question</span>
          <textarea
            id="classroom-question-input"
            value={questionText}
            onChange={(event) => onQuestionChange(event.target.value)}
            rows={3}
            placeholder="Type your doubt in one sentence"
            className="mt-2 min-h-24 w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          />
        </label>
        <button
          type="submit"
          disabled={!questionText.trim() || loadingAnswer}
          className="mt-3 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-500"
        >
          Ask Tutor
        </button>
        <div className="mt-3 flex flex-wrap gap-2">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onUsePrompt(prompt)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
            >
              {prompt}
            </button>
          ))}
        </div>
      </form>

      {discussionTurns.length > 0 && (
        <div className="mt-4 max-h-64 space-y-3 overflow-y-auto pr-1">
          {discussionTurns.map((turn) => (
            <div
              key={turn.id}
              className={`rounded-2xl border px-3 py-2 text-sm leading-6 ${
                turn.role === "student"
                  ? "border-slate-200 bg-slate-50 text-slate-800"
                  : "border-emerald-100 bg-emerald-50 text-emerald-950"
              }`}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] opacity-70">{turn.role === "student" ? "Student" : "Tutor"}</p>
              <p className="mt-1">{turn.content}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
