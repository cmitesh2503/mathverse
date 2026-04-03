"use client";

import { RefObject } from "react";
import { getAvatarProviderConfig } from "../lib/avatar-provider";

type TeacherAvatarProps = {
  avatarIframeUrl?: string | null;
  avatarLaunchUrl?: string | null;
  avatarProviderLabel?: string | null;
  avatarSetupHint?: string | null;
  chapter: string;
  isSpeaking: boolean;
  liveReady: boolean;
  name: string;
  stageMode?: "default" | "focus";
  status: string;
  summary: string;
  videoRef: RefObject<HTMLVideoElement | null>;
  videoStream: MediaStream | null;
};

const trimCopy = (value: string, maxLength: number) => {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength).trimEnd()}...`;
};

export default function TeacherAvatar({
  avatarIframeUrl,
  avatarLaunchUrl,
  avatarProviderLabel,
  avatarSetupHint,
  chapter,
  isSpeaking,
  liveReady,
  name,
  stageMode = "default",
  status,
  summary,
  videoRef,
  videoStream,
}: TeacherAvatarProps) {
  const avatarProvider = getAvatarProviderConfig();
  const effectiveIframeUrl = avatarIframeUrl ?? avatarProvider.src;
  const showIframe = avatarProvider.mode === "iframe" && Boolean(effectiveIframeUrl);
  const showVideoAvatar = avatarProvider.mode === "video" && Boolean(avatarProvider.src);
  const classroomMood = isSpeaking
    ? "Explaining now"
    : liveReady
      ? "Ready for your question"
      : "Preparing class";
  const isFocusStage = stageMode === "focus";
  const boardChapter = trimCopy(chapter, 48);
  const lessonNote = trimCopy(summary, 130);

  return (
    <div
      className={`overflow-hidden rounded-[1.9rem] bg-[linear-gradient(160deg,#f7e7d6_0%,#f3dcc4_36%,#e7d9ce_72%,#f8f4ee_100%)] p-[1px] ${
        isFocusStage
          ? "shadow-[0_36px_120px_rgba(84,55,28,0.2)]"
          : "shadow-[0_28px_90px_rgba(84,55,28,0.16)]"
      }`}
    >
      <style>{`
        @keyframes teacher-breathe {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-4px) scale(1.01); }
        }
        @keyframes teacher-nod {
          0%, 100% { transform: rotate(-0.8deg); }
          50% { transform: rotate(0.8deg); }
        }
        @keyframes tutor-blink {
          0%, 46%, 100% { transform: scaleY(1); }
          49% { transform: scaleY(0.14); }
          52% { transform: scaleY(1); }
        }
        @keyframes tutor-mouth {
          0%, 100% { transform: scaleY(0.9) scaleX(1); }
          50% { transform: scaleY(1.2) scaleX(1.04); }
        }
        @keyframes tutor-presence {
          0%, 100% { box-shadow: 0 0 0 0 rgba(234, 179, 8, 0.22); }
          50% { box-shadow: 0 0 0 10px rgba(234, 179, 8, 0); }
        }
        .teacher-portrait { animation: teacher-breathe 4.8s ease-in-out infinite; }
        .teacher-head { transform-origin: 144px 122px; animation: teacher-nod 6.4s ease-in-out infinite; }
        .teacher-eye { transform-origin: center; animation: tutor-blink 5.4s ease-in-out infinite; }
        .teacher-mouth { transform-origin: center; }
        .teacher-mouth-speaking { animation: tutor-mouth 0.34s ease-in-out infinite; }
        .teacher-presence { animation: tutor-presence 2s ease-out infinite; }
      `}</style>

      <div
        className={`rounded-[1.85rem] bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(250,246,240,0.98))] ${
          isFocusStage ? "p-6 lg:p-7" : "p-5"
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-amber-800">
              Live Math Class
            </div>
            <div className={`mt-2 font-semibold text-slate-900 ${isFocusStage ? "text-4xl" : "text-3xl"}`}>
              {name}
            </div>
            <div className={`mt-1 text-slate-600 ${isFocusStage ? "text-base" : "text-sm"}`}>
              CBSE mathematics teacher
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                isSpeaking
                  ? "border-amber-200 bg-amber-50 text-amber-900"
                  : liveReady
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-slate-200 bg-slate-50 text-slate-700"
              }`}
            >
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  isSpeaking
                    ? "teacher-presence bg-amber-500"
                    : liveReady
                      ? "bg-emerald-500"
                      : "bg-slate-300"
                }`}
              />
              {classroomMood}
            </div>
            <div className="rounded-full border border-slate-200 bg-white/85 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-600">
              {avatarProviderLabel || avatarProvider.label}
            </div>
          </div>
        </div>

        <div
          className={`relative mt-5 overflow-hidden rounded-[1.8rem] border border-white/80 bg-[linear-gradient(180deg,#fff9f2_0%,#f1e1ce_58%,#dcc2ac_100%)] ${
            isFocusStage ? "px-5 pb-5 pt-6" : "px-4 pb-4 pt-5"
          }`}
        >
          <div className="absolute inset-x-0 top-0 h-24 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.92),rgba(255,255,255,0))]" />
          <div
            className={`absolute inset-x-6 top-6 rounded-[1.5rem] bg-[linear-gradient(180deg,#305142_0%,#254235_100%)] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08),0_24px_50px_rgba(30,54,43,0.22)] ${
              isFocusStage ? "px-6 py-5" : "px-5 py-4"
            }`}
          >
            <div className="text-[10px] uppercase tracking-[0.34em] text-emerald-100/80">
              Today&apos;s Chapter
            </div>
            <div
              className={`mt-2 max-w-[72%] font-medium leading-tight text-emerald-50 ${
                isFocusStage ? "text-[1.45rem]" : "text-lg"
              }`}
            >
              {boardChapter}
            </div>
            <div className={`mt-3 max-w-[80%] leading-6 text-emerald-100/90 ${isFocusStage ? "text-base" : "text-sm"}`}>
              We will learn it step by step and solve it on the board together.
            </div>
          </div>

          <div className="absolute inset-x-0 bottom-0 h-24 bg-[linear-gradient(180deg,rgba(153,112,84,0)_0%,rgba(138,96,69,0.42)_100%)]" />

          <div
            className={`relative z-10 mt-24 flex items-end justify-center overflow-hidden rounded-[1.65rem] bg-[linear-gradient(180deg,rgba(255,248,241,0.2),rgba(255,255,255,0.02))] ${
              isFocusStage ? "min-h-[520px] xl:min-h-[68vh]" : "min-h-[325px]"
            }`}
          >
            {showIframe && effectiveIframeUrl ? (
              <iframe
                src={effectiveIframeUrl}
                title="Tutor avatar"
                className={`h-full w-full border-0 ${isFocusStage ? "min-h-[520px] xl:min-h-[68vh]" : "min-h-[325px]"}`}
                allow="camera; microphone; autoplay"
                allowFullScreen
              />
            ) : showVideoAvatar && avatarProvider.src ? (
              <video
                src={avatarProvider.src}
                autoPlay
                loop
                muted
                playsInline
                className={`h-full w-full object-cover ${isFocusStage ? "min-h-[520px] xl:min-h-[68vh]" : "min-h-[325px]"}`}
              />
            ) : (
              <div className="teacher-portrait relative z-10">
                <svg
                  width={isFocusStage ? "360" : "280"}
                  height={isFocusStage ? "440" : "340"}
                  viewBox="0 0 280 340"
                  className="drop-shadow-[0_30px_50px_rgba(79,50,32,0.28)]"
                >
                  <defs>
                    <linearGradient id="teacher-skin" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#f5d4c0" />
                      <stop offset="100%" stopColor="#d79f81" />
                    </linearGradient>
                    <linearGradient id="teacher-hair" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#50392d" />
                      <stop offset="100%" stopColor="#1e1713" />
                    </linearGradient>
                    <linearGradient id="teacher-jacket" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#32566d" />
                      <stop offset="100%" stopColor="#1f3140" />
                    </linearGradient>
                    <linearGradient id="teacher-blouse" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#fff8f0" />
                      <stop offset="100%" stopColor="#f2e4d7" />
                    </linearGradient>
                  </defs>

                  <ellipse cx="140" cy="318" rx="72" ry="14" fill="rgba(65,39,24,0.16)" />
                  <path
                    d="M72 306 C80 246 106 214 140 214 C174 214 200 246 208 306 Z"
                    fill="url(#teacher-jacket)"
                  />
                  <path
                    d="M111 214 L140 248 L169 214"
                    fill="url(#teacher-blouse)"
                  />

                  <g className="teacher-head">
                    <path
                      d="M94 124 C98 66 116 36 144 36 C176 36 198 70 198 126 C198 182 176 220 142 220 C106 220 88 180 94 124 Z"
                      fill="url(#teacher-skin)"
                    />
                    <path
                      d="M96 122 C84 86 88 48 122 36 C150 26 204 42 200 126 C184 106 166 100 146 100 C130 100 112 94 98 80 C98 100 98 112 96 122 Z"
                      fill="url(#teacher-hair)"
                    />
                    <path
                      d="M102 129 C112 122 122 121 132 125"
                      stroke="#4d3023"
                      strokeWidth="4"
                      strokeLinecap="round"
                      fill="none"
                    />
                    <path
                      d="M150 125 C160 120 171 121 180 128"
                      stroke="#4d3023"
                      strokeWidth="4"
                      strokeLinecap="round"
                      fill="none"
                    />
                    <g className="teacher-eye">
                      <ellipse cx="120" cy="140" rx="15" ry="8" fill="#fffdfb" />
                      <ellipse cx="167" cy="140" rx="15" ry="8" fill="#fffdfb" />
                      <circle cx="120" cy="141" r="5.5" fill="#332116" />
                      <circle cx="167" cy="141" r="5.5" fill="#332116" />
                    </g>
                    <path
                      d="M142 150 C136 166 136 176 144 181"
                      stroke="#bb866a"
                      strokeWidth="4"
                      strokeLinecap="round"
                      fill="none"
                    />
                    <ellipse
                      cx="144"
                      cy="194"
                      rx="15"
                      ry={isSpeaking ? 9 : 5.5}
                      fill="#9e5650"
                      className={`teacher-mouth ${isSpeaking ? "teacher-mouth-speaking" : ""}`}
                    />
                  </g>
                </svg>
              </div>
            )}

            {videoStream && (
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="absolute bottom-4 right-4 h-28 w-24 rounded-2xl border border-white/80 object-cover shadow-lg"
              />
            )}
          </div>
        </div>

        {!showIframe && !showVideoAvatar && (avatarSetupHint || avatarProvider.setupHint) && (
          <div className="mt-4 rounded-2xl border border-dashed border-amber-300 bg-amber-50/80 px-4 py-3 text-sm text-slate-700">
            <div className="font-semibold text-slate-900">Human avatar setup pending</div>
            <div className="mt-1 leading-6">{avatarSetupHint || avatarProvider.setupHint}</div>
          </div>
        )}

        <div className={`mt-4 grid gap-3 ${isFocusStage ? "xl:grid-cols-[1fr_1fr]" : "md:grid-cols-[1.1fr_0.9fr]"}`}>
          <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700">
              Ava&apos;s Pace
            </div>
            <div className={`mt-2 leading-6 text-slate-800 ${isFocusStage ? "text-[15px]" : "text-sm"}`}>
              {status}
            </div>
          </div>
          <div className={`rounded-2xl bg-slate-900 px-4 py-3 text-slate-100 ${isFocusStage ? "text-[15px]" : "text-sm"}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300">
              Class Focus
            </div>
            <div className="mt-2 leading-6 text-slate-100">{lessonNote}</div>
            {avatarLaunchUrl && (
              <a
                href={avatarLaunchUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex rounded-full bg-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-100 transition hover:bg-white/20"
              >
                Open Avatar Window
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
