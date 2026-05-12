"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { PageKey } from "../App";
import { TutorAvatar } from "../components/TutorAvatar";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { Whiteboard } from "../components/Whiteboard";
import { useTutorStream } from "../hooks/useTutorStream";
import { API_BASE_URL, type ClassResponse } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

type Props = {
  onNavigate: (page: PageKey) => void;
};

type IconProps = {
  className?: string;
};

function MicIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" stroke="currentColor" strokeWidth="2" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function HandIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 12V5.75a1.75 1.75 0 1 1 3.5 0V11M10.5 11V4.75a1.75 1.75 0 1 1 3.5 0V11M14 11V6.25a1.75 1.75 0 1 1 3.5 0V14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M7 12.5 5.7 11a1.9 1.9 0 0 0-2.75 2.62l5.25 6.04A5.6 5.6 0 0 0 12.42 21H14a5.5 5.5 0 0 0 5.5-5.5V10a1.75 1.75 0 1 0-3.5 0v3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function AlertIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 8v5M12 17h.01" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path
        d="M10.3 4.1 2.9 17.2A2.5 2.5 0 0 0 5.1 21h13.8a2.5 2.5 0 0 0 2.2-3.8L13.7 4.1a2 2 0 0 0-3.4 0Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function tutorWsUrl(sessionId: string) {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
  return `${base}/ws/tutor?session_id=${encodeURIComponent(sessionId)}&grade=10&subject=Mathematics`;
}

function downsampleBuffer(buffer: Float32Array, sourceRate: number, targetRate: number) {
  if (targetRate === sourceRate) return buffer;

  const ratio = sourceRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accumulator = 0;
    let count = 0;

    for (let index = offsetBuffer; index < nextOffsetBuffer && index < buffer.length; index += 1) {
      accumulator += buffer[index];
      count += 1;
    }

    result[offsetResult] = accumulator / Math.max(1, count);
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function floatTo16BitPcm(buffer: Float32Array) {
  const output = new ArrayBuffer(buffer.length * 2);
  const view = new DataView(output);

  for (let index = 0; index < buffer.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, buffer[index]));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return output;
}

function arrayBufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;

  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }

  return window.btoa(binary);
}

export default function Classroom({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const plan = useTutorStore((state) => state.plan);
  const setCurrentTopic = useTutorStore((state) => state.setCurrentTopic);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const setHomeworkQuestions = useTutorStore((state) => state.setHomeworkQuestions);
  const pendingClassResponse = useTutorStore((state) => state.pendingClassResponse);
  const setPendingClassResponse = useTutorStore((state) => state.setPendingClassResponse);
  const recordTutorSession = useTutorStore((state) => state.recordTutorSession);
  const recordResponse = useTutorStore((state) => state.recordResponse);
  const [answer, setAnswer] = useState("");
  const [micActive, setMicActive] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const consumedPendingRef = useRef(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const tutorSocketRef = useRef<WebSocket | null>(null);

  const onResponse = useCallback(
    (data: ClassResponse) => {
      const nextTopic = data.topic || data.chapter || data.content?.chapter;
      if (nextTopic) {
        setCurrentTopic(nextTopic);
      }
      setCurrentConcept(data.concept || data.content?.concept || null);
      if (data.question || data.example || data.content?.question || data.content?.example) {
        setCurrentQuestion(data.question || data.example || data.content?.question || data.content?.example || "");
      }
      const homework = data.homework || data.content?.homework || data.content?.questions || [];
      if (homework.length) {
        setHomeworkQuestions(homework);
      } else if (data.type !== "homework") {
        setHomeworkQuestions([]);
      }
      if (data.type === "evaluation" && data.correct !== null && data.correct !== undefined) {
        recordResponse({
          correct: data.correct,
          mistake_type: data.mistake_type,
          hint: data.hint,
          explanation: data.explanation,
          steps: data.steps,
          shortcut: data.shortcut,
          speed_hint: data.speed_hint,
          next_question: data.question,
        });
      }
      recordTutorSession({
        concept: data.concept || data.content?.concept,
        mistake_type: data.mistake_type,
        pattern: examMode === "jee" ? data.pattern || data.content?.pattern : null,
      });
    },
    [examMode, recordResponse, recordTutorSession, setCurrentConcept, setCurrentQuestion, setCurrentTopic, setHomeworkQuestions],
  );

  const { response, visibleSteps, isSpeaking, loading, error, paused, start, pauseOrResume, prime } = useTutorStream({
    sessionId,
    examMode,
    onResponse,
  });

  const classAllowed = examMode === "cbse" ? canUseFeature(plan, "cbse_class") : canUseFeature(plan, "jee_practice");

  useEffect(() => {
    if (!classAllowed) return;
    if (pendingClassResponse) {
      consumedPendingRef.current = true;
      prime(pendingClassResponse);
      onResponse(pendingClassResponse);
      setPendingClassResponse(null);
      return;
    }
    if (consumedPendingRef.current) return;
    void start({ grade: 10, subject: "math" });
  }, [classAllowed, onResponse, pendingClassResponse, prime, setPendingClassResponse, start]);

  useEffect(() => {
    return () => {
      stopMicrophone();
    };
  }, []);

  const concept = response?.concept || response?.content?.concept || "JEE Mathematics";
  const chapter = response?.chapter || response?.content?.chapter || "Live Class";
  const explanation = response?.explanation || response?.content?.explanation || "Class explanation will appear here.";
  const caption = response?.voice_text || response?.content?.voice_text || explanation;
  const whiteboard = response?.whiteboard || response?.content?.whiteboard;
  const whiteboardActions = response?.whiteboard_actions || response?.content?.whiteboard_actions || whiteboard?.actions || [];
  const pattern = response?.pattern || response?.content?.pattern;
  const shortcut = response?.shortcut || response?.content?.shortcut;
  const speedHint = response?.speed_hint || response?.content?.speed_hint;
  const notes = response?.session_notes || response?.content?.session_notes || response?.note_cards || response?.content?.note_cards || [];
  const homework = response?.homework || response?.content?.homework || response?.content?.questions || [];
  const isQuestion = response?.type === "question";

  const status = loading
    ? "Preparing the next step..."
    : micActive
      ? "Listening... speak now."
    : isSpeaking
      ? "Arvind Sir is explaining..."
      : paused
        ? "Raised hand. Tutor paused."
        : "Arvind Sir is listening.";

  const nextLabel =
    response?.next_action === "board_example"
      ? "Show Board Example"
      : response?.next_action === "question"
        ? "Ask Mini Check"
        : response?.next_action === "next_exercise"
          ? "Next Exercise"
          : response?.next_action === "homework" || response?.type === "homework"
            ? "Open Homework"
            : "Next Step";

  async function submitClassAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || loading) return;
    await start({ action: "next", answer });
    setAnswer("");
  }

  function goNext() {
    if (response?.type === "homework") {
      onNavigate("homework");
      return;
    }
    void start({ action: "next" });
  }

  function stopMicrophone() {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    void audioContextRef.current?.close();
    micStreamRef.current?.getTracks().forEach((track) => track.stop());

    if (tutorSocketRef.current?.readyState === WebSocket.OPEN) {
      tutorSocketRef.current.send(JSON.stringify({ type: "audio_stream_end" }));
      tutorSocketRef.current.close();
    }

    processorRef.current = null;
    sourceRef.current = null;
    audioContextRef.current = null;
    micStreamRef.current = null;
    tutorSocketRef.current = null;
    setMicActive(false);
  }

  function openTutorSocket() {
    return new Promise<WebSocket>((resolve, reject) => {
      const socket = new WebSocket(tutorWsUrl(sessionId));
      socket.onopen = () => resolve(socket);
      socket.onerror = () => reject(new Error("Could not open tutor audio WebSocket."));
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "live_warning" || payload.type === "live_error") {
            console.warn(payload.content || "Tutor audio stream warning");
          }
        } catch {
          console.debug("Tutor socket event:", event.data);
        }
      };
    });
  }

  async function startMicrophone() {
    try {
      setMicError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const socket = await openTutorSocket();
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        if (socket.readyState !== WebSocket.OPEN) return;

        const input = event.inputBuffer.getChannelData(0);
        const downsampled = downsampleBuffer(input, audioContext.sampleRate, 16000);
        const pcm = floatTo16BitPcm(downsampled);
        socket.send(
          JSON.stringify({
            type: "live_input_audio",
            data: arrayBufferToBase64(pcm),
          }),
        );
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      micStreamRef.current = stream;
      tutorSocketRef.current = socket;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;
      setMicActive(true);
    } catch (error) {
      console.error("Microphone access denied or unavailable.", error);
      setMicError("Microphone access denied or unavailable.");
      stopMicrophone();
      alert("Microphone access denied or unavailable.");
    }
  }

  function pushToTalk() {
    if (micActive) {
      stopMicrophone();
      return;
    }

    void startMicrophone();
  }

  function askForHelp() {
    void start({ action: "help" });
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-slate-950 pb-28 text-slate-50">
      {!classAllowed ? (
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <UpgradeNotice
            title={examMode === "jee" ? "JEE class mode is included in JEE Pro" : "Full voice classroom is included in CBSE Pro"}
            description="Free includes basic CBSE practice. Upgrade the active plan to unlock guided whiteboard classes, synced avatar voice, and saved class notes."
            recommendedPlan={examMode === "jee" ? "jee_pro" : "cbse_pro"}
          />
        </div>
      ) : (
        <div className="grid min-h-[calc(100vh-10rem)] gap-4 px-4 py-4 lg:grid-cols-[minmax(280px,30%)_minmax(0,70%)]">
          <aside className="flex min-h-[540px] flex-col rounded-lg border border-slate-800 bg-slate-900 shadow-2xl">
            <div className="border-b border-slate-800 px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Teacher Presence</p>
                  <h1 className="mt-1 text-xl font-semibold tracking-normal text-white">Arvind Sir</h1>
                </div>
                <span className={`h-3 w-3 rounded-full ${isSpeaking ? "bg-emerald-400" : paused ? "bg-amber-400" : "bg-sky-400"}`} />
              </div>
            </div>

            <div className="space-y-5 p-5">
              <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                <TutorAvatar
                  isSpeaking={isSpeaking}
                  label="JEE Tutor"
                  text={loading ? "Preparing..." : micActive ? "Listening" : isSpeaking ? "Teaching live" : paused ? "Paused" : "Ready"}
                />
              </div>

              <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${isSpeaking ? "bg-emerald-400" : paused ? "bg-amber-400" : "bg-sky-400"}`} />
                  <p className="text-sm font-semibold tracking-normal text-slate-100">{status}</p>
                </div>
                <div className="mt-4 max-h-56 overflow-y-auto rounded-md bg-slate-900 px-4 py-3 text-sm leading-7 tracking-normal text-slate-200">
                  {loading ? "One moment... setting up the next board move." : caption}
                </div>
              </div>

              <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Current Focus</p>
                <h2 className="mt-2 text-base font-semibold tracking-normal text-white">{chapter}</h2>
                <p className="mt-1 text-sm leading-6 tracking-normal text-slate-300">{concept}</p>
              </div>

              {error && <div className="rounded-lg border border-rose-400/40 bg-rose-950/60 p-4 text-sm text-rose-100">{error}</div>}
              {micError && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{micError}</div>}

              {isQuestion && (
                <form onSubmit={submitClassAnswer} className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <p className="text-sm font-semibold tracking-normal text-white">Mini Check</p>
                  <p className="mt-2 text-sm leading-6 tracking-normal text-slate-300">{response?.question || response?.content?.question}</p>
                  <div className="mt-4 flex gap-2">
                    <input
                      value={answer}
                      onChange={(event) => setAnswer(event.target.value)}
                      placeholder="Type your answer"
                      className="min-w-0 flex-1 rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                    />
                    <button
                      type="submit"
                      disabled={loading || !answer.trim()}
                      className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:bg-slate-700 disabled:text-slate-400"
                    >
                      Submit
                    </button>
                  </div>
                </form>
              )}

              {notes.length > 0 && (
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <p className="text-sm font-semibold tracking-normal text-white">Board Notes</p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 tracking-normal text-slate-300">
                    {notes.slice(0, 4).map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}

              {examMode === "jee" && (
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <p className="text-sm font-semibold tracking-normal text-white">JEE Pattern</p>
                  <p className="mt-2 text-sm leading-6 tracking-normal text-slate-300">{pattern || speedHint || "Watch the structure before expanding."}</p>
                  {shortcut && <p className="mt-2 text-sm leading-6 tracking-normal text-cyan-100">{shortcut}</p>}
                </div>
              )}

              {response?.type === "homework" && (
                <div className="rounded-lg border border-emerald-400/40 bg-emerald-950/50 p-4">
                  <p className="text-sm font-semibold tracking-normal text-emerald-100">Homework Ready</p>
                  <div className="mt-3 space-y-2">
                    {homework.slice(0, 3).map((question, index) => (
                      <p key={`${question.prompt || question.question || index}`} className="text-sm leading-6 tracking-normal text-emerald-50">
                        {index + 1}. {question.prompt || question.question || "Practice question"}
                      </p>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => onNavigate("homework")}
                    className="mt-4 rounded-md bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
                  >
                    Open Homework
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={goNext}
                  disabled={loading || isQuestion}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  {nextLabel}
                </button>
                <button
                  type="button"
                  onClick={() => void start({ action: "homework" })}
                  disabled={loading}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  Homework
                </button>
              </div>
            </div>
          </aside>

          <section className="min-h-[540px]">
            <Whiteboard steps={visibleSteps} whiteboard={whiteboard} whiteboardActions={whiteboardActions} />
          </section>
        </div>
      )}

      {classAllowed && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-700 bg-slate-950/95 px-4 py-3 shadow-2xl backdrop-blur">
          <div className="mx-auto grid max-w-4xl grid-cols-3 gap-3">
            <button
              type="button"
              onClick={pushToTalk}
              disabled={loading}
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-md px-2 py-3 text-xs font-bold tracking-normal transition disabled:bg-slate-700 disabled:text-slate-400 sm:flex-row sm:gap-2 sm:px-4 sm:text-sm ${
                micActive
                  ? "animate-pulse bg-rose-500 text-white hover:bg-rose-400"
                  : "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
              }`}
            >
              <MicIcon />
              <span className="text-center leading-tight">{micActive ? "Listening..." : "Push to Talk"}</span>
            </button>
            <button
              type="button"
              onClick={pauseOrResume}
              disabled={loading}
              className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-md border border-slate-600 bg-slate-800 px-2 py-3 text-xs font-semibold tracking-normal text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500 sm:flex-row sm:gap-2 sm:px-4 sm:text-sm"
            >
              <HandIcon />
              <span className="text-center leading-tight">Raise Hand</span>
            </button>
            <button
              type="button"
              onClick={askForHelp}
              disabled={loading}
              className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-md bg-rose-500 px-2 py-3 text-xs font-bold tracking-normal text-white transition hover:bg-rose-400 disabled:bg-slate-700 disabled:text-slate-400 sm:flex-row sm:gap-2 sm:px-4 sm:text-sm"
            >
              <AlertIcon />
              <span className="text-center leading-tight">I'm Stuck!</span>
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
