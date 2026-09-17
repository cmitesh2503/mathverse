import type { ReactNode } from "react";

type IconProps = {
  className?: string;
};

type Props = {
  isPlaying: boolean;
  isPaused: boolean;
  canPrevious: boolean;
  canNext: boolean;
  lessonProgress: number;
  onTogglePlay: () => void;
  onPreviousConcept: () => void;
  onNextConcept: () => void;
  onReplay: () => void;
  onAskQuestion: () => void;
};

function PlayIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M8 5v14l11-7L8 5Z" fill="currentColor" />
    </svg>
  );
}

function PauseIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 5h4v14H7V5Zm6 0h4v14h-4V5Z" fill="currentColor" />
    </svg>
  );
}

function PreviousIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M11 6 5 12l6 6M19 6l-6 6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NextIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m13 6 6 6-6 6M5 6l6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReplayIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 7v5h5M5 12a7 7 0 1 0 2-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function QuestionIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 17h.01M9.8 9a2.4 2.4 0 1 1 3.7 2c-.9.6-1.5 1.2-1.5 2.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke="currentColor" strokeWidth="2.2" />
    </svg>
  );
}

function ControlButton({
  children,
  disabled,
  onClick,
  title,
  primary,
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick: () => void;
  title: string;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className={`flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 ${
        primary ? "bg-blue-600 text-white shadow-sm hover:bg-blue-700" : "border border-slate-200 bg-white text-slate-800 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}

export function ClassroomControls({
  isPlaying,
  isPaused,
  canPrevious,
  canNext,
  lessonProgress,
  onTogglePlay,
  onPreviousConcept,
  onNextConcept,
  onReplay,
  onAskQuestion,
}: Props) {
  const playLabel = !isPlaying || isPaused ? "Play lesson" : "Pause lesson";

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(180px,260px)_minmax(0,1fr)_auto] lg:items-center">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Current lesson</p>
        <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-200">
          <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${lessonProgress}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <ControlButton title={playLabel} onClick={onTogglePlay} primary>
          {!isPlaying || isPaused ? <PlayIcon /> : <PauseIcon />}
          <span>{!isPlaying || isPaused ? "Play" : "Pause"}</span>
        </ControlButton>
        <ControlButton title="Previous concept" onClick={onPreviousConcept} disabled={!canPrevious}>
          <PreviousIcon />
          <span>Previous</span>
        </ControlButton>
        <ControlButton title="Next concept" onClick={onNextConcept} disabled={!canNext}>
          <NextIcon />
          <span>Next</span>
        </ControlButton>
        <ControlButton title="Replay explanation" onClick={onReplay}>
          <ReplayIcon />
          <span>Replay</span>
        </ControlButton>
        <ControlButton title="Ask a question" onClick={onAskQuestion}>
          <QuestionIcon />
          <span>Ask</span>
        </ControlButton>
      </div>

      <p className="text-sm font-semibold text-slate-600 lg:text-right">{lessonProgress}% synced</p>
    </div>
  );
}
