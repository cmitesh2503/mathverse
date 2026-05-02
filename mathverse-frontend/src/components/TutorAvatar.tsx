"use client";

type Props = {
  speaking?: boolean;
  isSpeaking?: boolean;
  label?: string;
  text?: string;
  mode?: "idle" | "speaking";
};

export function TutorAvatar({ speaking, isSpeaking, label = "AI Tutor", text, mode }: Props) {
  const active = Boolean(isSpeaking ?? speaking) || mode === "speaking";

  return (
    <div className="flex items-center gap-4">
      <div
        className={`relative grid h-16 w-16 place-items-center rounded-2xl bg-white text-3xl shadow-md ring-1 ring-slate-200 transition ${
          active ? "scale-[1.03] ring-4 ring-blue-200" : ""
        }`}
      >
        <span className={active ? "animate-pulse" : ""}>AI</span>
        {active && <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-emerald-400 shadow-sm" />}
      </div>
      <div>
        <p className="text-sm font-semibold uppercase text-slate-500">{label}</p>
        <p className="mt-1 text-sm font-medium text-slate-700">{text || (active ? "Voice stream playing" : "Ready to teach")}</p>
      </div>
    </div>
  );
}
