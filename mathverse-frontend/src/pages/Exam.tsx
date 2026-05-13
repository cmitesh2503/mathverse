"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TutorAvatar } from "../components/TutorAvatar";
import { Whiteboard } from "../components/Whiteboard";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { API_BASE_URL, type WhiteboardAction, type WhiteboardState } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

type IconProps = {
  className?: string;
};

type ConnectionState = "connecting" | "connected" | "disconnected";

function MicIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" stroke="currentColor" strokeWidth="2" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function tutorWsUrl(sessionId: string) {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
  return `${base}/ws/tutor?session_id=${encodeURIComponent(sessionId)}&grade=10&subject=Mathematics&mode=exam&exam=jee`;
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

function parseRecord(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  return payload as Record<string, unknown>;
}

function parseActions(payload: unknown): WhiteboardAction[] {
  if (!Array.isArray(payload)) return [];
  return payload.filter((item) => {
    const candidate = parseRecord(item);
    return Boolean(candidate && typeof candidate.action === "string");
  }) as WhiteboardAction[];
}

function parseWhiteboard(payload: unknown): WhiteboardState | null {
  const candidate = parseRecord(payload);
  if (!candidate) return null;
  return candidate as WhiteboardState;
}

function parseText(payload: unknown): string {
  return typeof payload === "string" ? payload : "";
}

function safeNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function Exam() {
  const sessionId = useTutorStore((state) => state.session_id);
  const plan = useTutorStore((state) => state.plan);
  const [caption, setCaption] = useState("Connecting to the AI Proctor...");
  const [studentTranscript, setStudentTranscript] = useState("");
  const [whiteboard, setWhiteboard] = useState<WhiteboardState | null>(null);
  const [whiteboardActions, setWhiteboardActions] = useState<WhiteboardAction[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [awaitingTurn, setAwaitingTurn] = useState(false);
  const [score, setScore] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [incorrectCount, setIncorrectCount] = useState(0);
  const [warnings, setWarnings] = useState(0);
  const [warningReason, setWarningReason] = useState<string | null>(null);
  const [isTerminated, setIsTerminated] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [mediaReady, setMediaReady] = useState(false);
  const assistantBufferRef = useRef("");
  const bootstrapSentRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoFrameTimerRef = useRef<number | null>(null);

  const examAllowed = canUseFeature(plan, "exam");

  const status = useMemo(() => {
    if (isTerminated) return "Exam terminated.";
    if (connectionError) return connectionError;
    if (cameraError) return cameraError;
    if (connectionState === "connecting") return "Connecting to live exam proctor...";
    if (connectionState === "disconnected") return "Live exam socket disconnected.";
    if (micActive) return "Listening... speak your option now.";
    if (awaitingTurn) return "Proctor is evaluating your answer...";
    return "Live JEE mock test active.";
  }, [awaitingTurn, cameraError, connectionError, connectionState, isTerminated, micActive]);

  const applyScoreUpdate = useCallback((update: { score: number; correct: number; wrong: number }) => {
    setScore(update.score);
    setCorrectCount(update.correct);
    setIncorrectCount(update.wrong);
  }, []);

  const stopMicrophone = useCallback(() => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    void audioContextRef.current?.close();

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio_stream_end" }));
      setAwaitingTurn(true);
    }

    processorRef.current = null;
    sourceRef.current = null;
    audioContextRef.current = null;
    setMicActive(false);
  }, []);

  const stopCameraStream = useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    setMediaReady(false);
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    if (videoFrameTimerRef.current) {
      window.clearInterval(videoFrameTimerRef.current);
      videoFrameTimerRef.current = null;
    }
  }, []);

  const sendExamMessage = useCallback((message: string) => {
    if (isTerminated) return false;
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setConnectionError("Live exam socket is not connected.");
      return false;
    }

    socket.send(
      JSON.stringify({
        message,
        mode: "exam",
        context: { exam: "jee" },
      }),
    );
    setConnectionError(null);
    setAwaitingTurn(true);
    return true;
  }, [isTerminated]);

  const handleProctorActions = useCallback(
    (actions: WhiteboardAction[]) => {
      const drawableActions: WhiteboardAction[] = [];
      actions.forEach((action) => {
        if (action.action === "issue_warning") {
          const reason = action.reason || "Suspicious activity detected.";
          const warningCount = safeNumber(action.warnings, NaN);
          setWarnings((current) => {
            if (Number.isFinite(warningCount) && warningCount >= current) return warningCount;
            return current + 1;
          });
          setWarningReason(reason);
          return;
        }

        if (action.action === "terminate_exam") {
          const reason = action.reason || "Maximum warnings exceeded.";
          setWarningReason(reason);
          setIsTerminated(true);
          setAwaitingTurn(false);
          stopMicrophone();
          return;
        }

        drawableActions.push(action);
      });

      return drawableActions;
    },
    [stopMicrophone],
  );

  const maybeSendInitialExamPayload = useCallback(() => {
    if (bootstrapSentRef.current || isTerminated) return;
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const hasVideoTrack = Boolean(mediaStreamRef.current?.getVideoTracks().length);
    const message = hasVideoTrack
      ? "Camera feed active and student face visible in frame. Start the JEE mock test."
      : "Start the JEE mock test.";

    socket.send(
      JSON.stringify({
        message,
        mode: "exam",
        context: { exam: "jee" },
      }),
    );
    bootstrapSentRef.current = true;
    setConnectionError(null);
    setAwaitingTurn(true);
  }, [isTerminated]);

  const handleSocketMessage = useCallback((rawData: string) => {
    let payload: unknown = null;
    try {
      payload = JSON.parse(rawData);
    } catch {
      return;
    }

    const message = parseRecord(payload);
    if (!message) return;

    const type = parseText(message.type);
    const action = parseText(message.action);

    if (action) {
      handleProctorActions([message as WhiteboardAction]);
    }

    if (!type) return;

    if (type === "assistant_turn_start") {
      assistantBufferRef.current = "";
      return;
    }

    if (type === "assistant_text") {
      const chunk = parseText(message.content);
      if (!chunk) return;
      assistantBufferRef.current = `${assistantBufferRef.current}${chunk}`;
      setCaption(assistantBufferRef.current);
      return;
    }

    if (type === "transcript") {
      const nextTranscript = parseText(message.content);
      if (nextTranscript) setStudentTranscript(nextTranscript);
      return;
    }

    if (type === "state") {
      const state = parseRecord(message.state);
      if (!state) return;
      const board = parseWhiteboard(state.whiteboard);
      if (!board) return;
      setWhiteboard({ ...board, actions: [] });
      return;
    }

    if (type === "whiteboard_actions") {
      const incomingActions = parseActions(message.actions);
      const drawableActions = handleProctorActions(incomingActions);
      if (drawableActions.length) {
        setWhiteboardActions((current) => [...current, ...drawableActions]);
      }
      return;
    }

    if (type === "assistant_turn_complete") {
      setAwaitingTurn(false);
      const spoken = parseText(message.spoken_response) || assistantBufferRef.current;
      if (spoken) {
        assistantBufferRef.current = spoken;
        setCaption(spoken);
      }

      const incomingActions = parseActions(message.whiteboard_actions);
      const drawableActions = handleProctorActions(incomingActions);
      if (drawableActions.length) {
        setWhiteboardActions((current) => [...current, ...drawableActions]);
      }

      const state = parseRecord(message.state);
      if (state) {
        const board = parseWhiteboard(state.whiteboard);
        if (board) {
          setWhiteboard({ ...board, actions: [] });
        }
      }
      return;
    }

    if (type === "live_warning" || type === "live_error") {
      setConnectionError(parseText(message.content) || "Live exam warning from server.");
      if (type === "live_error") setAwaitingTurn(false);
    }
  }, [handleProctorActions]);

  useEffect(() => {
    if (!examAllowed) return;
    bootstrapSentRef.current = false;
    setConnectionState("connecting");
    setConnectionError(null);
    setCaption("Connecting to the AI Proctor...");
    setStudentTranscript("");
    setWhiteboardActions([]);
    setWarnings(0);
    setWarningReason(null);
    setIsTerminated(false);
    assistantBufferRef.current = "";

    const socket = new WebSocket(tutorWsUrl(sessionId));
    socketRef.current = socket;

    socket.onopen = () => {
      setConnectionState("connected");
      setCaption("AI Proctor connected. Initializing your JEE mock test...");
      maybeSendInitialExamPayload();
    };

    socket.onmessage = (event) => {
      if (typeof event.data !== "string") return;
      handleSocketMessage(event.data);
    };

    socket.onerror = () => {
      setConnectionError("Could not communicate with the live exam socket.");
    };

    socket.onclose = () => {
      setConnectionState("disconnected");
      setAwaitingTurn(false);
      setMicActive(false);
    };

    return () => {
      stopMicrophone();
      stopCameraStream();
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [examAllowed, handleSocketMessage, maybeSendInitialExamPayload, sessionId, stopCameraStream, stopMicrophone]);

  useEffect(() => {
    if (!examAllowed) return;
    let cancelled = false;

    async function setupMedia() {
      try {
        setCameraError(null);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        mediaStreamRef.current = stream;
        setMediaReady(true);
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = stream;
          void localVideoRef.current.play().catch(() => {});
        }
        maybeSendInitialExamPayload();
      } catch (error) {
        console.error("Camera or microphone access denied or unavailable.", error);
        setCameraError("Camera and microphone access are required for live proctoring.");
      }
    }

    void setupMedia();
    return () => {
      cancelled = true;
    };
  }, [examAllowed, maybeSendInitialExamPayload]);

  useEffect(() => {
    if (!examAllowed || !mediaReady || isTerminated) {
      if (videoFrameTimerRef.current) {
        window.clearInterval(videoFrameTimerRef.current);
        videoFrameTimerRef.current = null;
      }
      return;
    }

    const timer = window.setInterval(() => {
      const socket = socketRef.current;
      const stream = mediaStreamRef.current;
      const video = localVideoRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN || !stream || !video) return;
      if (!stream.getVideoTracks().length || video.readyState < 2) return;

      const canvas = frameCanvasRef.current || document.createElement("canvas");
      frameCanvasRef.current = canvas;

      const width = Math.max(240, video.videoWidth || 320);
      const height = Math.max(180, video.videoHeight || 240);
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) return;

      context.drawImage(video, 0, 0, width, height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.45);
      const base64Payload = dataUrl.split(",")[1];
      if (!base64Payload) return;

      socket.send(
        JSON.stringify({
          type: "live_input_video",
          data: base64Payload,
          mime_type: "image/jpeg",
        }),
      );
    }, 1800);

    videoFrameTimerRef.current = timer;
    return () => {
      window.clearInterval(timer);
      if (videoFrameTimerRef.current === timer) {
        videoFrameTimerRef.current = null;
      }
    };
  }, [examAllowed, isTerminated, mediaReady]);

  async function startMicrophone() {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setMicError("Live exam socket is not connected.");
      return;
    }
    const stream = mediaStreamRef.current;
    if (!stream) {
      setMicError("Camera and microphone are not ready yet.");
      return;
    }

    try {
      setMicError(null);
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

      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;
      setMicActive(true);
      setAwaitingTurn(false);
      setStudentTranscript("");
    } catch (error) {
      console.error("Microphone access denied or unavailable.", error);
      setMicError("Microphone access denied or unavailable.");
      stopMicrophone();
    }
  }

  function pushToTalk() {
    if (isTerminated) return;
    if (micActive) {
      stopMicrophone();
      return;
    }
    void startMicrophone();
  }

  function chooseOption(option: "A" | "B" | "C" | "D") {
    if (isTerminated) return;
    sendExamMessage(`I choose Option ${option}`);
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-slate-950 pb-28 text-slate-50">
      {examAllowed && warningReason && !isTerminated && (
        <div className="fixed inset-x-0 top-16 z-50 animate-pulse border-y border-amber-300 bg-gradient-to-r from-amber-500/90 via-rose-500/80 to-amber-500/90 px-4 py-2 text-sm font-bold text-slate-950 shadow-lg">
          Warning {warnings}/2: {warningReason}
        </div>
      )}

      {!examAllowed && (
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <UpgradeNotice
            title="Timed exam mode is included in JEE Lite"
            description="Unlock timed tests, score tracking, and rank-estimation foundations by switching to JEE Lite or JEE Pro."
            recommendedPlan="jee_lite"
          />
        </div>
      )}
      {examAllowed && (
        <div className="grid min-h-[calc(100vh-10rem)] gap-4 px-4 py-4 lg:grid-cols-[minmax(280px,30%)_minmax(0,70%)]">
          <aside className="flex min-h-[540px] flex-col rounded-lg border border-slate-800 bg-slate-900 shadow-2xl">
            <div className="border-b border-slate-800 px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Live Mock Test</p>
                  <h1 className="mt-1 text-xl font-semibold tracking-normal text-white">AI Proctor</h1>
                </div>
                <span
                  className={`h-3 w-3 rounded-full ${
                    connectionState === "connected" ? (micActive ? "bg-emerald-400" : "bg-sky-400") : "bg-rose-400"
                  }`}
                />
              </div>
            </div>

            <div className="space-y-5 p-5">
              <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                <TutorAvatar
                  isSpeaking={awaitingTurn}
                  label="JEE Proctor"
                  text={
                    connectionState !== "connected"
                      ? "Connecting..."
                      : micActive
                        ? "Listening live"
                        : awaitingTurn
                          ? "Evaluating response"
                          : "Ready for your next option"
                  }
                />
              </div>

              <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      connectionState !== "connected" ? "bg-rose-400" : micActive ? "bg-emerald-400" : "bg-sky-400"
                    }`}
                  />
                  <p className="text-sm font-semibold tracking-normal text-slate-100">{status}</p>
                </div>
                <div className="mt-4 max-h-56 overflow-y-auto rounded-md bg-slate-900 px-4 py-3 text-sm leading-7 tracking-normal text-slate-200">
                  {caption}
                </div>
                {studentTranscript && (
                  <div className="mt-3 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs tracking-normal text-slate-300">
                    You: {studentTranscript}
                  </div>
                )}
              </div>

              {connectionError && <div className="rounded-lg border border-rose-400/40 bg-rose-950/60 p-4 text-sm text-rose-100">{connectionError}</div>}
              {micError && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{micError}</div>}
              {cameraError && <div className="rounded-lg border border-rose-400/40 bg-rose-950/60 p-4 text-sm text-rose-100">{cameraError}</div>}
            </div>
          </aside>

          <section className="flex min-h-[540px] flex-col gap-4">
            {!isTerminated ? (
              <>
                <div className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 shadow-lg sm:px-5">
                  <div className="flex flex-wrap items-center gap-4 text-sm font-semibold text-slate-100 sm:gap-6">
                    <span>Current Score: {score}</span>
                    <span>Correct: {correctCount}</span>
                    <span>Incorrect: {incorrectCount}</span>
                    <span>Warnings: {warnings}/2</span>
                  </div>
                </div>
                <Whiteboard steps={[]} whiteboard={whiteboard} whiteboardActions={whiteboardActions} onScoreUpdate={applyScoreUpdate} />
              </>
            ) : (
              <div className="grid min-h-[540px] place-items-center rounded-lg border border-rose-500 bg-rose-950/90 p-8 text-center shadow-2xl">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-rose-200">Mock Test Locked</p>
                  <h2 className="mt-3 text-4xl font-black leading-tight text-rose-50 sm:text-5xl">
                    EXAM TERMINATED DUE TO SUSPICIOUS ACTIVITY
                  </h2>
                  <p className="mt-4 text-lg font-semibold text-rose-100">{warningReason || "Maximum warnings exceeded."}</p>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {examAllowed && mediaReady && (
        <div className="pointer-events-none fixed bottom-24 right-4 z-40 w-44 overflow-hidden rounded-lg border border-slate-600 bg-slate-900/90 shadow-2xl sm:w-52">
          <div className="border-b border-slate-700 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-300">
            Student Camera
          </div>
          <video ref={localVideoRef} autoPlay muted playsInline className="h-28 w-full object-cover sm:h-32" />
        </div>
      )}

      {examAllowed && !isTerminated && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-700 bg-slate-950/95 px-4 py-3 shadow-2xl backdrop-blur">
          <div className="mx-auto flex max-w-4xl items-center justify-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={pushToTalk}
              disabled={connectionState !== "connected" || !mediaReady}
              className={`flex min-h-12 min-w-40 items-center justify-center gap-2 rounded-md px-4 py-3 text-sm font-bold tracking-normal transition disabled:bg-slate-700 disabled:text-slate-400 ${
                micActive ? "animate-pulse bg-rose-500 text-white hover:bg-rose-400" : "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
              }`}
            >
              <MicIcon />
              <span>{micActive ? "Listening..." : "Push to Talk"}</span>
            </button>

            {(["A", "B", "C", "D"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => chooseOption(option)}
                disabled={connectionState !== "connected"}
                className="grid h-12 w-12 place-items-center rounded-full border border-slate-600 bg-slate-800 text-base font-bold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                aria-label={`Choose option ${option}`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
