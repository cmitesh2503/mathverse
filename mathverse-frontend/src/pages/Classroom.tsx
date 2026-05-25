"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PageKey } from "../App";
import { TutorAvatar } from "../components/TutorAvatar";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { Whiteboard } from "../components/Whiteboard";
import { useTutorStream } from "../hooks/useTutorStream";
import { API_BASE_URL, type ClassResponse, type ExamMode, type TeachingLanguage } from "../services/api";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

type Props = {
  onNavigate: (page: PageKey) => void;
};

type IconProps = {
  className?: string;
};

type DiscussionTurn = {
  id: string;
  role: "student" | "tutor";
  content: string;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  start: () => void;
  stop: () => void;
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
const LIVE_INPUT_SAMPLE_RATE = 16000;
const AUTO_CONTINUE_AFTER_SPEECH_MS = 1800;

const CLASSROOM_GRADES = [10, 11, 12] as const;
type ClassroomGrade = (typeof CLASSROOM_GRADES)[number];
const TEACHING_LANGUAGES: Array<{ value: TeachingLanguage; label: string; speechLang: string }> = [
  { value: "en-IN", label: "English (India)", speechLang: "en-IN" },
  { value: "hi-IN", label: "Hindi", speechLang: "hi-IN" },
  { value: "gu-IN", label: "Gujarati", speechLang: "gu-IN" },
];

const CBSE_GRADE_10_CHAPTERS = [
  { slug: "real_numbers", title: "Real Numbers" },
  { slug: "polynomials", title: "Polynomials" },
  { slug: "pair_of_linear_equations", title: "Pair of Linear Equations in Two Variables" },
  { slug: "quadratic_equations", title: "Quadratic Equations" },
  { slug: "arithmetic_progressions", title: "Arithmetic Progressions" },
  { slug: "triangles", title: "Triangles" },
  { slug: "coordinate_geometry", title: "Coordinate Geometry" },
  { slug: "introduction_to_trigonometry", title: "Introduction to Trigonometry" },
  { slug: "applications_of_trigonometry", title: "Some Applications of Trigonometry" },
  { slug: "circles", title: "Circles" },
  { slug: "constructions", title: "Constructions" },
  { slug: "areas_related_to_circles", title: "Areas Related to Circles" },
  { slug: "surface_areas_and_volumes", title: "Surface Areas and Volumes" },
  { slug: "statistics", title: "Statistics" },
  { slug: "probability", title: "Probability" },
] as const;

function tutorWsUrl(sessionId: string, grade: ClassroomGrade, examMode: ExamMode, topicSlug?: string) {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
  const params = new URLSearchParams({
    session_id: sessionId,
    grade: String(grade),
    subject: "Mathematics",
    mode: "class",
    exam: examMode,
  });
  if (topicSlug) {
    params.set("topic_slug", topicSlug);
  }
  return `${base}/ws/tutor?${params.toString()}`;
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
  const [teachingLanguage, setTeachingLanguage] = useState<TeachingLanguage>("en-IN");
  const [selectedChapterSlug, setSelectedChapterSlug] = useState<(typeof CBSE_GRADE_10_CHAPTERS)[number]["slug"]>(
    CBSE_GRADE_10_CHAPTERS[0].slug,
  );
  const [classStarted, setClassStarted] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [liveDiscussionActive, setLiveDiscussionActive] = useState(false);
  const [nextCoolingDown, setNextCoolingDown] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [timeoutMessage, setTimeoutMessage] = useState<string | null>(null);
  const [doubtText, setDoubtText] = useState("");
  const [discussionTurns, setDiscussionTurns] = useState<DiscussionTurn[]>([]);
  const consumedPendingRef = useRef(false);
  const assistantDraftRef = useRef("");
  const activeAssistantTurnIdRef = useRef<string | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const analyserCheckIntervalRef = useRef<number | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const inputProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const inputSilenceRef = useRef<GainNode | null>(null);
  const tutorSocketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const isMicStoppingRef = useRef(false);
  const lastAudioActivityRef = useRef<number | null>(null);
  const inputSpeechDetectedRef = useRef(false);
  const liveTurnEndingRef = useRef(false);
  const liveSilenceTimerRef = useRef<number | null>(null);
  const autoListenTimerRef = useRef<number | null>(null);
  const autoContinueTimerRef = useRef<number | null>(null);
  const wasSpeakingRef = useRef(false);
  const lastAutoContinueKeyRef = useRef("");
  const autoContinueInFlightRef = useRef(false);
  const liveDiscussionActiveRef = useRef(false);
  const speechRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const speechTranscriptRef = useRef("");
  const outputAudioContextRef = useRef<AudioContext | null>(null);
  const outputPlaybackCursorRef = useRef(0);
  const activePlaybackSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const latestClassSnapshotRef = useRef<{ chapter: string; concept: string; visibleSteps: string[] }>({
    chapter: "Live Class",
    concept: "Mathematics",
    visibleSteps: [],
  });
  const queueAutoListenRef = useRef<() => void>(() => {});

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

  const { response, visibleSteps, activeStepIndex, isSpeaking, loading, error, paused, start, pauseOrResume, stop, prime } = useTutorStream({
    sessionId,
    examMode,
    teachingLanguage,
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
  const selectedChapter =
    CBSE_GRADE_10_CHAPTERS.find((chapter) => chapter.slug === selectedChapterSlug) ?? CBSE_GRADE_10_CHAPTERS[0];
  const selectedTeachingLanguage =
    TEACHING_LANGUAGES.find((language) => language.value === teachingLanguage) ?? TEACHING_LANGUAGES[0];
  const selectedChapterInput = useMemo(
    () =>
      examMode === "cbse" && selectedGrade === 10
        ? { chapter: selectedChapter.title, chapter_slug: selectedChapter.slug }
        : {},
    [examMode, selectedChapter.slug, selectedChapter.title, selectedGrade],
  );

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
    void start({ action: "start", grade: selectedGrade, subject: "math", ...selectedChapterInput });
  }, [
    classAllowed,
    classStarted,
    onResponse,
    pendingClassResponse,
    prime,
    selectedChapterInput,
    selectedGrade,
    setPendingClassResponse,
    start,
  ]);

  const concept = response?.concept || response?.content?.concept || `${examLabel} Mathematics`;
  const chapter = response?.chapter || response?.content?.chapter || "Live Class";
  const liveChapterSlug =
    CBSE_GRADE_10_CHAPTERS.find((item) => item.title.toLowerCase() === String(chapter || "").toLowerCase())?.slug ||
    selectedChapterSlug;
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

  useEffect(() => {
    latestClassSnapshotRef.current = { chapter, concept, visibleSteps };
  }, [chapter, concept, visibleSteps]);

  useEffect(() => {
    liveDiscussionActiveRef.current = liveDiscussionActive;
  }, [liveDiscussionActive]);
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
      ? "Listening live... speak naturally, then pause."
    : liveDiscussionActive
      ? "Live discussion is open. I will listen again after the tutor replies."
    : isSpeaking
      ? "Arvind Sir is explaining..."
      : paused
        ? "Raised hand. Tutor paused."
        : "Class continues automatically after each explanation.";

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
      await start({ action: "start", grade: selectedGrade, subject: "math", ...selectedChapterInput });
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

  useEffect(() => {
    if (isSpeaking) {
      wasSpeakingRef.current = true;
      return;
    }

    if (!wasSpeakingRef.current) return;
    wasSpeakingRef.current = false;

    if (autoContinueTimerRef.current) {
      window.clearTimeout(autoContinueTimerRef.current);
      autoContinueTimerRef.current = null;
    }

    const canAutoContinue =
      classAllowed &&
      classStarted &&
      response &&
      response.type !== "homework" &&
      response.type !== "question" &&
      !sessionExpired &&
      !paused &&
      !micActive &&
      !liveDiscussionActive &&
      !loading &&
      !nextCoolingDown;

    if (!canAutoContinue) return;

    const turnKey = [
      response.chapter || response.content?.chapter || "",
      response.topic || response.content?.topic || "",
      response.problem_no || response.problem_statement || "",
      visibleSteps.slice(0, 3).join("|"),
    ].join("::");
    if (turnKey && turnKey === lastAutoContinueKeyRef.current) return;
    lastAutoContinueKeyRef.current = turnKey;

    autoContinueTimerRef.current = window.setTimeout(() => {
      if (
        autoContinueInFlightRef.current ||
        sessionExpired ||
        paused ||
        micActive ||
        liveDiscussionActiveRef.current ||
        loading ||
        nextCoolingDown
      ) {
        return;
      }

      const action =
        response.next_action === "next_exercise"
          ? "next_exercise"
          : response.next_action === "next_pdf_exercise"
            ? "next_pdf_exercise"
            : "continue";

      autoContinueInFlightRef.current = true;
      setNextCoolingDown(true);
      window.setTimeout(() => setNextCoolingDown(false), 1200);
      void start({ action, grade: selectedGrade, subject: "math" })
        .catch((error) => {
          console.error("Auto-continue failed.", error);
        })
        .finally(() => {
          autoContinueInFlightRef.current = false;
        });
    }, AUTO_CONTINUE_AFTER_SPEECH_MS);

    return () => {
      if (autoContinueTimerRef.current) {
        window.clearTimeout(autoContinueTimerRef.current);
        autoContinueTimerRef.current = null;
      }
    };
  }, [
    classAllowed,
    classStarted,
    isSpeaking,
    liveDiscussionActive,
    loading,
    micActive,
    nextCoolingDown,
    paused,
    response,
    selectedGrade,
    sessionExpired,
    start,
    visibleSteps,
  ]);

  async function askDoubt(event?: FormEvent<HTMLFormElement>, presetQuestion?: string) {
    event?.preventDefault();
    const question = (presetQuestion ?? doubtText).trim();
    if (!question || sessionExpired) return;

    stop();
    setDoubtText("");
    setDiscussionTurns((current) => [
      ...current,
      {
        id: `student-${Date.now()}`,
        role: "student",
        content: question,
      },
    ]);

    try {
      const boardProblem =
        response?.problem_statement ||
        response?.board_problem ||
        response?.whiteboard?.problem ||
        response?.content?.whiteboard?.problem ||
        response?.question ||
        response?.example ||
        null;
      await start({
        question,
        grade: selectedGrade,
        subject: "math",
        board_problem: boardProblem,
        board_steps: visibleSteps,
        whiteboard_context: whiteboard,
      });
    } catch (error) {
      console.error("Failed to ask classroom doubt.", error);
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

  const sendStopListeningSignal = useCallback((transcript = "") => {
    const cleanedTranscript = transcript.trim();
    sendSocketPayload({
      type: "control",
      action: "stop_listening",
      transcript: cleanedTranscript || undefined,
      mode: "class",
      context: { exam: examMode, grade: selectedGrade, teaching_language: teachingLanguage, chapter, chapter_slug: liveChapterSlug, topic: concept },
    });
    sendSocketPayload({ type: "audio_stream_end" });
  }, [chapter, concept, examMode, liveChapterSlug, selectedGrade, sendSocketPayload, teachingLanguage]);

  const base64ToUint8Array = (value: string) => {
    const binary = window.atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  };

  const pcm16ToFloat32 = (bytes: Uint8Array) => {
    const sampleCount = Math.floor(bytes.byteLength / 2);
    const floats = new Float32Array(sampleCount);
    const dataView = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let index = 0; index < sampleCount; index += 1) {
      floats[index] = dataView.getInt16(index * 2, true) / 0x8000;
    }
    return floats;
  };

  const stopLiveAudioPlayback = useCallback(() => {
    activePlaybackSourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {}
      try {
        source.disconnect();
      } catch {}
    });
    activePlaybackSourcesRef.current = [];
    outputPlaybackCursorRef.current = 0;
  }, []);

  function queueAutoListen() {
    if (!liveDiscussionActiveRef.current || sessionExpired || micActive) return;
    if (autoListenTimerRef.current) {
      window.clearTimeout(autoListenTimerRef.current);
      autoListenTimerRef.current = null;
    }
    const delayMs = activePlaybackSourcesRef.current.length ? 500 : 700;
    autoListenTimerRef.current = window.setTimeout(() => {
      autoListenTimerRef.current = null;
      if (!liveDiscussionActiveRef.current || sessionExpired || micActive) return;
      if (activePlaybackSourcesRef.current.length) {
        queueAutoListen();
        return;
      }
      void startMicrophone();
    }, delayMs);
  }
  queueAutoListenRef.current = queueAutoListen;

  const playLiveAudioChunk = useCallback(async (base64Data: string, sampleRate: number) => {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;

    if (!outputAudioContextRef.current) {
      outputAudioContextRef.current = new AudioContextClass();
    }

    const audioContext = outputAudioContextRef.current;
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    const pcmBytes = base64ToUint8Array(base64Data);
    const float32 = pcm16ToFloat32(pcmBytes);
    const audioBuffer = audioContext.createBuffer(1, float32.length, sampleRate);
    audioBuffer.copyToChannel(float32, 0);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    activePlaybackSourcesRef.current.push(source);
    source.onended = () => {
      activePlaybackSourcesRef.current = activePlaybackSourcesRef.current.filter((item) => item !== source);
      if (!activePlaybackSourcesRef.current.length) {
        queueAutoListenRef.current();
      }
    };

    const startAt = Math.max(audioContext.currentTime + 0.02, outputPlaybackCursorRef.current);
    outputPlaybackCursorRef.current = startAt + audioBuffer.duration;
    source.start(startAt);
  }, []);

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
      liveTurnEndingRef.current = true;

      try {
        if (analyserCheckIntervalRef.current) {
          window.clearInterval(analyserCheckIntervalRef.current);
          analyserCheckIntervalRef.current = null;
        }
        if (liveSilenceTimerRef.current) {
          window.clearTimeout(liveSilenceTimerRef.current);
          liveSilenceTimerRef.current = null;
        }
        if (speechRecognitionRef.current) {
          try {
            speechRecognitionRef.current.stop();
          } catch {}
          speechRecognitionRef.current = null;
          await new Promise((resolve) => window.setTimeout(resolve, 250));
        }

        inputProcessorRef.current?.disconnect();
        sourceRef.current?.disconnect();
        inputSilenceRef.current?.disconnect();
        analyserRef.current = null;
        inputProcessorRef.current = null;
        inputSilenceRef.current = null;
        
        if (audioContextRef.current && audioContextRef.current.state !== "closed") {
          try {
            await audioContextRef.current.close();
          } catch (e) {
            console.debug("Audio context close error (expected):", e);
          }
        }

        micStreamRef.current?.getTracks().forEach((track) => {
          try {
            track.stop();
          } catch (e) {
            console.debug("Track stop error:", e);
          }
        });

        if (inputSpeechDetectedRef.current) {
          sendStopListeningSignal(speechTranscriptRef.current);
        }
        
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
        speechTranscriptRef.current = "";
        lastAudioActivityRef.current = null;
        analyserCheckIntervalRef.current = null;
        inputSpeechDetectedRef.current = false;
        liveTurnEndingRef.current = false;
        
        setMicActive(false);
        isMicStoppingRef.current = false;
      }
    },
    [closeTutorSocket, sendSocketPayload, sendStopListeningSignal],
  );

  const openTutorSocket = useCallback(() => {
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
      const socket = new WebSocket(tutorWsUrl(sessionId, selectedGrade, examMode, liveChapterSlug));
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
          if (payload.type === "live_warning") {
            console.warn(payload.content || "Tutor audio stream warning");
            setTimeoutMessage(payload.content || "Live voice fallback is active.");
          }
          if (payload.type === "live_error") {
            console.warn(payload.content || "Tutor audio stream warning");
            setMicError(payload.content || "Native Gemini Live audio is not connected.");
          }
          if (payload.type === "live_status") {
            setMicError(null);
            setTimeoutMessage("Gemini Live audio connected.");
          }
          if (payload.type === "transcript" && payload.content) {
            setTimeoutMessage(`Heard: ${payload.content}`);
          }
          if (payload.type === "squelch") {
            stopLiveAudioPlayback();
          }
          if (payload.type === "live_audio" && payload.data) {
            void playLiveAudioChunk(String(payload.data), Number(payload.sample_rate || 24000));
          }
          if (payload.type === "user_turn" && payload.content) {
            setDiscussionTurns((current) => [
              ...current,
              {
                id: `student-${Date.now()}`,
                role: "student",
                content: String(payload.content),
              },
            ]);
          }
          if (payload.type === "assistant_turn_start") {
            assistantDraftRef.current = "";
            activeAssistantTurnIdRef.current = `tutor-${Date.now()}`;
            setDiscussionTurns((current) => [
              ...current,
              {
                id: activeAssistantTurnIdRef.current || `tutor-${Date.now()}`,
                role: "tutor",
                content: "",
              },
            ]);
          }
          if (payload.type === "assistant_text" && payload.content) {
            assistantDraftRef.current += String(payload.content);
            const turnId = activeAssistantTurnIdRef.current;
            setDiscussionTurns((current) =>
              current.map((turn) =>
                turn.id === turnId ? { ...turn, content: assistantDraftRef.current } : turn,
              ),
            );
          }
          if (payload.type === "assistant_turn_complete") {
            const state = payload.state;
            const spokenResponse = String(payload.spoken_response || assistantDraftRef.current || "").trim();
            const actions = Array.isArray(payload.whiteboard_actions) ? payload.whiteboard_actions : state?.whiteboard_actions || [];
            const { chapter: currentChapter, concept: currentConcept, visibleSteps: currentVisibleSteps } = latestClassSnapshotRef.current;
            const board = state?.whiteboard || {
              title: currentChapter,
              subtitle: "Arvind Sir's smart blackboard",
              chalk_lines: currentVisibleSteps,
              actions,
            };
            const steps = Array.isArray(board.chalk_lines)
              ? board.chalk_lines
              : actions
                  .map((action: { content?: unknown; text?: unknown; label?: unknown }) => action.content || action.text || action.label)
                  .filter((item: unknown): item is string => typeof item === "string" && item.trim().length > 0);

            if (spokenResponse || steps.length) {
              prime({
                type: "teach",
                chapter: currentChapter,
                topic: currentChapter,
                concept: currentConcept,
                explanation: spokenResponse || "Arvind Sir answered your doubt.",
                voice_text: spokenResponse || "Arvind Sir answered your doubt.",
                steps,
                whiteboard: board,
                whiteboard_actions: actions,
                correct: null,
                mistake_type: null,
                next_action: "continue",
                session_time_left_seconds: payload.session_time_left_seconds,
                session_duration_seconds: payload.session_duration_seconds,
                session_expired: Boolean(payload.session_expired),
              });
            }
            assistantDraftRef.current = "";
            activeAssistantTurnIdRef.current = null;
            queueAutoListenRef.current();

          }
          if (payload.type === "next_problem" && Array.isArray(payload.whiteboard_actions)) {
            console.debug("Ignoring prefetched next_problem; auto-flow requests one turn at a time.");
          }
        } catch {
          console.debug("Tutor socket event:", event.data);
        }
      };
    });
  }, [examMode, liveChapterSlug, playLiveAudioChunk, prime, selectedGrade, sessionId, stopLiveAudioPlayback]);

  useEffect(() => {
    if (!classAllowed || !classStarted) return;
    let cancelled = false;

    void openTutorSocket().catch((error) => {
      if (cancelled) return;
      console.error("Failed to open tutor websocket for class push", error);
    });

    return () => {
      cancelled = true;
      closeTutorSocket();
    };
  }, [classAllowed, classStarted, closeTutorSocket, openTutorSocket]);

  async function startMicrophone() {
    try {
      if (micActive) return;
      if (autoListenTimerRef.current) {
        window.clearTimeout(autoListenTimerRef.current);
        autoListenTimerRef.current = null;
      }
      setMicError(null);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const socket = await openTutorSocket();
      socket.send(
        JSON.stringify({
          type: "context_update",
          mode: "class",
          context: {
            exam: examMode,
            grade: selectedGrade,
            teaching_language: teachingLanguage,
            chapter,
            chapter_slug: liveChapterSlug,
            topic: concept,
          },
          whiteboard,
          whiteboard_actions: whiteboardActions,
          visible_steps: visibleSteps,
        }),
      );
      stop();
      stopLiveAudioPlayback();
      
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass();
      await audioContext.resume();
      
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      const silence = audioContext.createGain();
      silence.gain.value = 0;
      inputSpeechDetectedRef.current = false;
      liveTurnEndingRef.current = false;
      lastAudioActivityRef.current = Date.now();
      speechTranscriptRef.current = "";
      setTimeoutMessage(null);

      const SpeechRecognitionClass =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognitionClass) {
        try {
          const recognition = new SpeechRecognitionClass() as BrowserSpeechRecognition;
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = selectedTeachingLanguage.speechLang;
          recognition.onresult = (event: any) => {
            let transcript = "";
            for (let index = 0; index < event.results.length; index += 1) {
              transcript += event.results[index][0]?.transcript || "";
            }
            speechTranscriptRef.current = transcript.trim();
            if (speechTranscriptRef.current) {
              setTimeoutMessage(`Heard: ${speechTranscriptRef.current}`);
            }
          };
          recognition.onerror = () => {
            speechRecognitionRef.current = null;
          };
          recognition.start();
          speechRecognitionRef.current = recognition;
        } catch (error) {
          console.debug("Browser speech recognition unavailable.", error);
        }
      }

      processor.onaudioprocess = (event) => {
        if (!tutorSocketRef.current || tutorSocketRef.current.readyState !== WebSocket.OPEN || liveTurnEndingRef.current) {
          return;
        }

        const inputData = event.inputBuffer.getChannelData(0);
        let energy = 0;
        for (let index = 0; index < inputData.length; index += 1) {
          const sample = inputData[index] ?? 0;
          energy += sample * sample;
        }
        const rms = Math.sqrt(energy / Math.max(1, inputData.length));
        if (!inputSpeechDetectedRef.current && rms <= 0.008) {
          return;
        }

        if (rms > 0.012) {
          if (!inputSpeechDetectedRef.current) {
            inputSpeechDetectedRef.current = true;
            stop();
            stopLiveAudioPlayback();
          }
          lastAudioActivityRef.current = Date.now();
          if (liveSilenceTimerRef.current) {
            window.clearTimeout(liveSilenceTimerRef.current);
          }
          liveSilenceTimerRef.current = window.setTimeout(() => {
            void stopMicrophone();
          }, 3200);
        }

        const downsampled = downsampleBuffer(inputData, audioContext.sampleRate, LIVE_INPUT_SAMPLE_RATE);
        const pcm = floatTo16BitPcm(downsampled);
        tutorSocketRef.current.send(
          JSON.stringify({
            type: "live_input_audio",
            data: arrayBufferToBase64(pcm),
            sample_rate: LIVE_INPUT_SAMPLE_RATE,
          }),
        );
      };

      source.connect(processor);
      processor.connect(silence);
      silence.connect(audioContext.destination);

      // Store references
      micStreamRef.current = stream;
      tutorSocketRef.current = socket;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      analyserRef.current = analyser;
      inputProcessorRef.current = processor;
      inputSilenceRef.current = silence;
      
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
    stop();
    void start({ action: "help", grade: selectedGrade, subject: "math" });
  }

  function startLiveDiscussion() {
    if (sessionExpired) return;
    liveDiscussionActiveRef.current = true;
    setLiveDiscussionActive(true);
    void startMicrophone().catch((error) => {
      console.error("Unable to start microphone capture.", error);
      setMicError("Unable to start microphone capture.");
      liveDiscussionActiveRef.current = false;
      setLiveDiscussionActive(false);
      setMicActive(false);
      void stopMicrophone({ keepSocket: false });
    });
  }

  function stopLiveDiscussion() {
    liveDiscussionActiveRef.current = false;
    setLiveDiscussionActive(false);
    if (autoListenTimerRef.current) {
      window.clearTimeout(autoListenTimerRef.current);
      autoListenTimerRef.current = null;
    }
    stopLiveAudioPlayback();
    if (micActive) {
      void stopMicrophone({ keepSocket: false });
    } else {
      closeTutorSocket();
    }
  }

  function handleMicPress() {
    if (sessionExpired) return;
    if (!classStarted || micActive) return;
    if (liveDiscussionActive) {
      stopLiveDiscussion();
    } else {
      startLiveDiscussion();
    }
  }

  function handleMicRelease() {
    if (!micActive) return;
    void stopMicrophone().catch((error) => {
      console.error("Unable to stop microphone capture.", error);
      setMicError("Unable to stop microphone capture.");
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
      liveDiscussionActiveRef.current = false;
      if (autoListenTimerRef.current) {
        window.clearTimeout(autoListenTimerRef.current);
        autoListenTimerRef.current = null;
      }
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
            <h2 className="mt-2 text-2xl font-semibold text-white">Choose Your {examLabel} Class</h2>
            <p className="mt-2 text-sm text-slate-300">Select grade and chapter before Arvind Sir starts the session.</p>

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

            <label className="mt-5 block">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Teaching language</span>
              <select
                value={teachingLanguage}
                onChange={(event) => setTeachingLanguage(event.target.value as TeachingLanguage)}
                className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold text-slate-100 outline-none transition focus:border-cyan-300"
              >
                {TEACHING_LANGUAGES.map((language) => (
                  <option key={language.value} value={language.value}>
                    {language.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs leading-5 text-slate-400">
                Hindi and Gujarati explanations keep math terms, formulas, and board labels in English.
              </p>
            </label>

            {examMode === "cbse" && selectedGrade === 10 ? (
              <>
              <label className="mt-5 block">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Chapter</span>
                <select
                  value={selectedChapterSlug}
                  onChange={(event) => setSelectedChapterSlug(String(event.target.value))}
                  className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold text-slate-100 outline-none transition focus:border-cyan-300"
                >
                  {CBSE_GRADE_10_CHAPTERS.map((chapter, index) => (
                    <option key={chapter.slug} value={chapter.slug}>
                      Chapter {index + 1}: {chapter.title}
                    </option>
                  ))}
                </select>
              </label>
              </>
            ) : null}

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

              <label className="block rounded-lg border border-slate-700 bg-slate-950 p-4">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Teaching language</span>
                <select
                  value={teachingLanguage}
                  onChange={(event) => setTeachingLanguage(event.target.value as TeachingLanguage)}
                  className="mt-2 w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-100 outline-none transition focus:border-cyan-300"
                >
                  {TEACHING_LANGUAGES.map((language) => (
                    <option key={language.value} value={language.value}>
                      {language.label}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs leading-5 text-slate-400">
                  Math terms and formulas stay in English for Hindi/Gujarati.
                </p>
              </label>

              {error && <div className="rounded-lg border border-rose-400/40 bg-rose-950/60 p-4 text-sm text-rose-100">{error}</div>}
              {micError && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{micError}</div>}
              {timeoutMessage && <div className="rounded-lg border border-amber-400/40 bg-amber-950/60 p-4 text-sm text-amber-100">{timeoutMessage}</div>}

              <form onSubmit={askDoubt} className="rounded-lg border border-cyan-400/30 bg-cyan-950/25 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold tracking-normal text-cyan-100">Live Doubt</p>
                    <p className="mt-1 text-xs leading-5 text-cyan-200/80">Ask while Arvind Sir is solving.</p>
                  </div>
                  {isSpeaking && (
                    <span className="rounded-full bg-amber-400/15 px-3 py-1 text-xs font-semibold text-amber-100">
                      Interrupt ready
                    </span>
                  )}
                </div>
                <div className="mt-3 flex items-end gap-2">
                  <textarea
                    value={doubtText}
                    onChange={(event) => setDoubtText(event.target.value)}
                    placeholder="Type your full doubt"
                    rows={3}
                    className="min-h-24 min-w-0 flex-1 resize-y rounded-md border border-cyan-500/40 bg-slate-950 px-3 py-2 text-sm leading-6 text-white outline-none focus:border-cyan-300"
                  />
                  <button
                    type="submit"
                    disabled={sessionExpired || !doubtText.trim()}
                    className="rounded-md bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 disabled:bg-slate-700 disabled:text-slate-400"
                  >
                    Ask
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {["Please explain this step again", "Why did we use this formula?", "I did not understand the last step"].map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void askDoubt(undefined, prompt)}
                      disabled={sessionExpired}
                      className="rounded-full border border-cyan-500/30 px-3 py-1.5 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/10 disabled:text-slate-500"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </form>

              {discussionTurns.length > 0 && (
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <p className="text-sm font-semibold tracking-normal text-white">Doubt Discussion</p>
                  <div className="mt-3 max-h-52 space-y-3 overflow-y-auto pr-1">
                    {discussionTurns.slice(-6).map((turn) => (
                      <div
                        key={turn.id}
                        className={`rounded-md px-3 py-2 text-sm leading-6 ${
                          turn.role === "student"
                            ? "bg-cyan-400/10 text-cyan-50"
                            : "bg-slate-800 text-slate-100"
                        }`}
                      >
                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                          {turn.role === "student" ? "Student" : "Arvind Sir"}
                        </p>
                        <p className="mt-1">{turn.content || "Answering..."}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
              onClick={micActive ? handleMicRelease : handleMicPress}
              disabled={sessionExpired}
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-md px-2 py-3 text-xs font-bold tracking-normal transition disabled:bg-slate-700 disabled:text-slate-400 sm:flex-row sm:gap-2 sm:px-4 sm:text-sm ${
                micActive
                  ? "animate-pulse bg-rose-500 text-white hover:bg-rose-400"
                  : liveDiscussionActive
                    ? "border border-rose-400 bg-slate-900 text-rose-100 hover:bg-rose-950"
                  : "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
              }`}
            >
              <MicIcon />
              <span className="text-center leading-tight">
                {micActive ? "End Turn" : liveDiscussionActive ? "Stop Live" : "Live Discuss"}
              </span>
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
