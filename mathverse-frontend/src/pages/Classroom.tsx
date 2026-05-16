"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { PageKey } from "../App";
import { TutorAvatar } from "../components/TutorAvatar";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { Whiteboard } from "../components/Whiteboard";
import { useTutorStream } from "../hooks/useTutorStream";
import { API_BASE_URL, type ClassResponse, type ExamMode } from "../services/api";
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

const SILENCE_TIMEOUT_MS = 15000;
const SILENCE_RMS_THRESHOLD = 0.004;
const CLASS_SESSION_DURATION_SECONDS = 45 * 60;

const CLASSROOM_GRADES = [10, 11, 12] as const;
type ClassroomGrade = (typeof CLASSROOM_GRADES)[number];

function tutorWsUrl(sessionId: string, grade: ClassroomGrade, examMode: ExamMode) {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
  return `${base}/ws/tutor?session_id=${encodeURIComponent(sessionId)}&grade=${grade}&subject=Mathematics&mode=class&exam=${encodeURIComponent(examMode)}`;
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
  const [selectedGrade, setSelectedGrade] = useState<ClassroomGrade>(10);
  const [classStarted, setClassStarted] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [nextCoolingDown, setNextCoolingDown] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [timeoutMessage, setTimeoutMessage] = useState<string | null>(null);
  const consumedPendingRef = useRef(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const analyserCheckIntervalRef = useRef<number | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const tutorSocketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const isMicStoppingRef = useRef(false);
  const lastAudioActivityRef = useRef<number | null>(null);

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

  const { response, visibleSteps, activeStepIndex, isSpeaking, loading, error, paused, start, pauseOrResume, prime } = useTutorStream({
    sessionId,
    examMode,
    onResponse,
  });

  useEffect(() => {
    if (examMode === "cbse" && selectedGrade !== 10) {
      setSelectedGrade(10);
    }
  }, [examMode, selectedGrade]);

  const classAllowed = examMode === "cbse" ? canUseFeature(plan, "cbse_class") : canUseFeature(plan, "jee_practice");
  const gradeOptions: ClassroomGrade[] = examMode === "cbse" ? [10] : [...CLASSROOM_GRADES];
  const examLabel = examMode.toUpperCase();
  const tutorLabel = examMode === "cbse" ? "CBSE Tutor" : "JEE Tutor";

  useEffect(() => {
    if (!classAllowed) return;
    if (!classStarted) return;
    if (pendingClassResponse) {
      consumedPendingRef.current = true;
      prime(pendingClassResponse);
      onResponse(pendingClassResponse);
      setPendingClassResponse(null);
      return;
    }
    if (consumedPendingRef.current) return;
    void start({ action: "start", grade: selectedGrade, subject: "math" });
  }, [classAllowed, classStarted, onResponse, pendingClassResponse, prime, selectedGrade, setPendingClassResponse, start]);

  const concept = response?.concept || response?.content?.concept || `${examLabel} Mathematics`;
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
  const sessionExpired = Boolean(response?.session_expired);
  const sessionTimeLeftSeconds = Math.max(
    0,
    Number(response?.session_time_left_seconds ?? CLASS_SESSION_DURATION_SECONDS),
  );
  const sessionDurationSeconds = Math.max(
    1,
    Number(response?.session_duration_seconds ?? CLASS_SESSION_DURATION_SECONDS),
  );
  const formatClock = (totalSeconds: number) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  const status = !classStarted
    ? "Select grade and start your class."
    : sessionExpired
    ? "Today's 45-minute session is complete."
    : loading
    ? "Preparing the next step..."
    : micActive
      ? "Listening... speak now."
    : isSpeaking
      ? "Arvind Sir is explaining..."
      : paused
        ? "Raised hand. Tutor paused."
        : "Class is paused for you. Click Next when you want the next explanation.";

  const nextLabel = sessionExpired
    ? "Start New 45-min Session"
    : response?.next_action === "board_example"
      ? "Show Board Example"
      : response?.next_action === "question"
        ? "Ask Mini Check"
      : response?.next_action === "next_exercise"
          ? "Next Exercise"
          : response?.next_action === "homework" || response?.type === "homework"
            ? "Open Homework"
            : "Next";

  async function submitClassAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || loading) return;
    await start({ action: "next", answer, grade: selectedGrade, subject: "math" });
    setAnswer("");
  }

  async function goNext() {
    if (sessionExpired) {
      await start({ action: "start", grade: selectedGrade, subject: "math" });
      return;
    }
    if (response?.type === "homework") {
      onNavigate("homework");
      return;
    }
    if (loading || nextCoolingDown) return;

    setNextCoolingDown(true);
    window.setTimeout(() => setNextCoolingDown(false), 2000);

    try {
      const action =
        response?.next_action === "next_exercise"
          ? "next_exercise"
          : response?.next_action === "next_pdf_exercise"
            ? "next_pdf_exercise"
            : "continue";
      await start({ action, grade: selectedGrade, subject: "math" });
    } catch (error) {
      console.error("Failed to advance class topic.", error);
    }
  }

  async function skipTopic() {
    if (sessionExpired || loading || nextCoolingDown) return;
    setNextCoolingDown(true);
    window.setTimeout(() => setNextCoolingDown(false), 2000);
    try {
      await start({ action: "next_topic", grade: selectedGrade, subject: "math" });
    } catch (error) {
      console.error("Failed to skip to the next topic.", error);
    }
  }

  async function goPrevious() {
    if (sessionExpired || loading || nextCoolingDown) return;
    setNextCoolingDown(true);
    window.setTimeout(() => setNextCoolingDown(false), 1200);
    try {
      await start({ action: "previous_problem", grade: selectedGrade, subject: "math" });
    } catch (error) {
      console.error("Failed to go to previous problem.", error);
    }
  }

  async function refreshProblem() {
    if (sessionExpired || loading || nextCoolingDown) return;
    setNextCoolingDown(true);
    window.setTimeout(() => setNextCoolingDown(false), 1200);
    try {
      await start({ action: "refresh_problem", grade: selectedGrade, subject: "math" });
    } catch (error) {
      console.error("Failed to refresh problem.", error);
    }
  }

  const sendSocketPayload = useCallback((payload: Record<string, unknown>) => {
    const socket = tutorSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      socket.send(JSON.stringify(payload));
      return true;
    } catch (error) {
      console.error("Failed to send payload over tutor socket.", error);
      setMicError("Connection dropped while sending audio.");
      return false;
    }
  }, []);

  const sendStopListeningSignal = useCallback(() => {
    sendSocketPayload({ type: "control", action: "stop_listening" });
    sendSocketPayload({ type: "audio_stream_end" });
  }, [sendSocketPayload]);

  const closeTutorSocket = useCallback(() => {
    if (tutorSocketRef.current?.readyState === WebSocket.OPEN || tutorSocketRef.current?.readyState === WebSocket.CONNECTING) {
      tutorSocketRef.current.close();
    }
    tutorSocketRef.current = null;
  }, []);

  const stopMicrophone = useCallback(
    async ({ keepSocket = true }: { keepSocket?: boolean } = {}) => {
      if (isMicStoppingRef.current) return;
      isMicStoppingRef.current = true;

      try {
        // Clear silence detection interval
        if (analyserCheckIntervalRef.current) {
          window.clearInterval(analyserCheckIntervalRef.current);
          analyserCheckIntervalRef.current = null;
        }

        // Disconnect audio nodes
        sourceRef.current?.disconnect();
        analyserRef.current = null;
        
        // Close audio context
        if (audioContextRef.current && audioContextRef.current.state !== "closed") {
          try {
            await audioContextRef.current.close();
          } catch (e) {
            console.debug("Audio context close error (expected):", e);
          }
        }

        // Stop media recorder
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          await new Promise<void>((resolve) => {
            const cleanup = () => resolve();
            recorder.onstop = cleanup;
            recorder.onerror = cleanup;
            try {
              recorder.stop();
            } catch {
              cleanup();
            }
          });
        }

        // Flush recorded audio to socket
        const bufferedBlob =
          mediaChunksRef.current.length > 0 ? new Blob(mediaChunksRef.current, { type: mediaRecorderRef.current?.mimeType || "audio/webm" }) : null;
        if (bufferedBlob && bufferedBlob.size > 0) {
          try {
            const buffer = await bufferedBlob.arrayBuffer();
            sendSocketPayload({
              type: "recorded_audio_buffer",
              data: arrayBufferToBase64(buffer),
              mime_type: bufferedBlob.type || "audio/webm",
            });
          } catch (error) {
            console.error("Failed to flush recorded audio buffer.", error);
          }
        }

        // Stop all media tracks
        micStreamRef.current?.getTracks().forEach((track) => {
          try {
            track.stop();
          } catch (e) {
            console.debug("Track stop error:", e);
          }
        });

        // Send explicit stop listening signals
        sendStopListeningSignal();
        
        if (!keepSocket) {
          closeTutorSocket();
        }
      } catch (error) {
        console.error("Failed to stop microphone cleanly.", error);
      } finally {
        // CRITICAL: Reset all state references
        sourceRef.current = null;
        analyserRef.current = null;
        audioContextRef.current = null;
        mediaRecorderRef.current = null;
        mediaChunksRef.current = [];
        micStreamRef.current = null;
        lastAudioActivityRef.current = null;
        analyserCheckIntervalRef.current = null;
        
        // CRITICAL: Force UI state reset
        setMicActive(false);
        isMicStoppingRef.current = false;
      }
    },
    [closeTutorSocket, sendSocketPayload, sendStopListeningSignal],
  );

  function openTutorSocket() {
    if (tutorSocketRef.current?.readyState === WebSocket.OPEN) {
      return Promise.resolve(tutorSocketRef.current);
    }

    if (tutorSocketRef.current?.readyState === WebSocket.CONNECTING) {
      return new Promise<WebSocket>((resolve, reject) => {
        const socket = tutorSocketRef.current;
        if (!socket) {
          reject(new Error("Could not open tutor audio WebSocket."));
          return;
        }
        socket.addEventListener("open", () => resolve(socket), { once: true });
        socket.addEventListener("error", () => reject(new Error("Could not open tutor audio WebSocket.")), { once: true });
      });
    }

    return new Promise<WebSocket>((resolve, reject) => {
      const socket = new WebSocket(tutorWsUrl(sessionId, selectedGrade, examMode));
      tutorSocketRef.current = socket;

      socket.onopen = () => resolve(socket);

      socket.onerror = () => reject(new Error("Could not open tutor audio WebSocket."));

      socket.onclose = () => {
        if (tutorSocketRef.current === socket) {
          tutorSocketRef.current = null;
        }
      };

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
      if (micActive) return;
      setMicError(null);
      
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const socket = await openTutorSocket();
      
      // Create audio context
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass();
      
      // Create analyser (NOT deprecated like ScriptProcessor)
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      
      // Connect source to analyser
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      
      // Start media recorder for final audio capture
      const mediaRecorder = new MediaRecorder(stream);
      mediaChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          mediaChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onerror = (error) => {
        console.error("MediaRecorder error:", error);
        setMicError("Microphone recording failed. Please retry.");
        void stopMicrophone();
      };
      
      mediaRecorder.start(250); // Timeslice every 250ms

      // Set up silence detection using AnalyserNode (not deprecated)
      lastAudioActivityRef.current = Date.now();
      setTimeoutMessage(null);
      
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      const checkAudioActivity = () => {
        if (!analyser) return;
        
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        
        // If there's audio activity above threshold, update timestamp
        if (average > SILENCE_RMS_THRESHOLD * 1000) {
          lastAudioActivityRef.current = Date.now();
        }
      };
      
      // Run silence check every 100ms
      analyserCheckIntervalRef.current = window.setInterval(checkAudioActivity, 100);

      // Store references
      micStreamRef.current = stream;
      tutorSocketRef.current = socket;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      analyserRef.current = analyser;
      mediaRecorderRef.current = mediaRecorder;
      
      // Update UI
      setMicActive(true);
    } catch (error) {
      console.error("Microphone access denied or unavailable.", error);
      setMicError("Microphone access denied or unavailable.");
      setMicActive(false);
      await stopMicrophone({ keepSocket: false });
    }
  }

  function askForHelp() {
    if (sessionExpired) return;
    void start({ action: "help", grade: selectedGrade, subject: "math" });
  }

  function handleMicPress() {
    if (sessionExpired) return;
    if (!classStarted || loading || micActive) return;
    void startMicrophone().catch((error) => {
      console.error("Unable to start microphone capture.", error);
      setMicError("Unable to start microphone capture.");
      setMicActive(false);
      void stopMicrophone({ keepSocket: false });
    });
  }

  function handleMicRelease() {
    // CRITICAL: Always reset UI immediately on release
    setMicActive(false);
    
    if (!micActive) return;
    
    // Stop recording in background
    void stopMicrophone().catch((error) => {
      console.error("Unable to stop microphone capture.", error);
      setMicError("Unable to stop microphone capture.");
      // Force reset even on error
      setMicActive(false);
    });
  }

  function beginClassroom() {
    consumedPendingRef.current = false;
    setTimeoutMessage(null);
    setClassStarted(true);
  }

  useEffect(() => {
    if (!micActive) return;
    const timer = window.setInterval(() => {
      const lastAudioTs = lastAudioActivityRef.current;
      if (!lastAudioTs) return;
      if (Date.now() - lastAudioTs < SILENCE_TIMEOUT_MS) return;
      setTimeoutMessage("Microphone auto-stopped after 15 seconds of silence.");
      void stopMicrophone();
    }, 1000);

    return () => window.clearInterval(timer);
  }, [micActive, stopMicrophone]);

  useEffect(() => {
    return () => {
      // Cleanup on unmount: stop everything
      setMicActive(false);
      if (analyserCheckIntervalRef.current) {
        window.clearInterval(analyserCheckIntervalRef.current);
      }
      void stopMicrophone({ keepSocket: false });
      closeTutorSocket();
    };
  }, [closeTutorSocket, stopMicrophone]);

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
      ) : !classStarted ? (
        <div className="mx-auto flex min-h-[calc(100vh-12rem)] w-full max-w-xl items-center px-4 py-8 sm:px-6">
          <div className="w-full rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Class Setup</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Choose Your {examLabel} Grade</h2>
            <p className="mt-2 text-sm text-slate-300">Select grade before Arvind Sir starts the session and chapter agenda.</p>

            <div className="mt-5 grid grid-cols-2 gap-3">
              {gradeOptions.map((grade) => (
                <button
                  key={grade}
                  type="button"
                  onClick={() => setSelectedGrade(grade)}
                  className={`rounded-lg border px-4 py-3 text-sm font-semibold transition ${
                    selectedGrade === grade
                      ? "border-cyan-300 bg-cyan-400 text-slate-950"
                      : "border-slate-600 bg-slate-800 text-slate-100 hover:bg-slate-700"
                  }`}
                >
                  Grade {grade}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={beginClassroom}
              className="mt-5 w-full rounded-lg bg-cyan-400 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-300"
            >
              Start Class
            </button>
          </div>
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
                  label={tutorLabel}
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
                <p className={`mt-2 text-xs font-semibold tracking-[0.12em] ${sessionExpired ? "text-rose-300" : "text-cyan-200"}`}>
                  Session Time Left: {formatClock(sessionTimeLeftSeconds)} / {formatClock(sessionDurationSeconds)}
                </p>
              </div>

              {error && <div className="rounded-lg border border-rose-400/40 bg-rose-950/60 p-4 text-sm text-rose-100">{error}</div>}
              {micError && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{micError}</div>}
              {timeoutMessage && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{timeoutMessage}</div>}

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

              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <button
                  type="button"
                  onClick={() => void goNext()}
                  disabled={loading || isQuestion || nextCoolingDown}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  {nextCoolingDown ? "Loading..." : nextLabel}
                </button>
                <button
                  type="button"
                  onClick={() => void goPrevious()}
                  disabled={loading || isQuestion || sessionExpired || nextCoolingDown}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => void skipTopic()}
                  disabled={loading || isQuestion || sessionExpired || nextCoolingDown}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  Skip Topic
                </button>
                <button
                  type="button"
                  onClick={() => void refreshProblem()}
                  disabled={loading || sessionExpired || nextCoolingDown}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={pauseOrResume}
                  disabled={loading || sessionExpired}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  {paused ? "Resume" : "Pause"}
                </button>
                <button
                  type="button"
                  onClick={() => void start({ action: "homework", grade: selectedGrade, subject: "math" })}
                  disabled={loading || sessionExpired}
                  className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500"
                >
                  Homework
                </button>
              </div>
            </div>
          </aside>

          <section className="min-h-[540px]">
            <Whiteboard
              steps={visibleSteps}
              whiteboard={whiteboard}
              whiteboardActions={whiteboardActions}
              activeStepIndex={activeStepIndex}
            />
          </section>
        </div>
      )}

      {classAllowed && classStarted && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-700 bg-slate-950/95 px-4 py-3 shadow-2xl backdrop-blur">
          <div className="mx-auto grid max-w-4xl grid-cols-3 gap-3">
            <button
              type="button"
              onMouseDown={handleMicPress}
              onMouseUp={handleMicRelease}
              onMouseLeave={handleMicRelease}
              onTouchStart={(e) => {
                e.preventDefault();
                handleMicPress();
              }}
              onTouchEnd={(e) => {
                e.preventDefault();
                handleMicRelease();
              }}
              disabled={loading || sessionExpired}
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
              disabled={loading || sessionExpired}
              className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-md border border-slate-600 bg-slate-800 px-2 py-3 text-xs font-semibold tracking-normal text-slate-100 transition hover:bg-slate-700 disabled:text-slate-500 sm:flex-row sm:gap-2 sm:px-4 sm:text-sm"
            >
              <HandIcon />
              <span className="text-center leading-tight">Raise Hand</span>
            </button>
            <button
              type="button"
              onClick={askForHelp}
              disabled={loading || sessionExpired}
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
