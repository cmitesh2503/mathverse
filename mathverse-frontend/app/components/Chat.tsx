"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import ClassWhiteboard, { type WhiteboardPayload } from "./ClassWhiteboard";
import TeacherAvatar from "./TeacherAvatar";
import { getAvatarProviderConfig } from "../lib/avatar-provider";
import { useChatStore } from "../store/useChatStore";

const ENV_API_BASE = process.env.NEXT_PUBLIC_API_BASE;
const ENV_WS_BASE = process.env.NEXT_PUBLIC_WS_BASE;
const STUDENT_ID_KEY = "mathverse-student-id";
const LIVE_INPUT_SAMPLE_RATE = 16000;

const dedupeValues = (values: Array<string | undefined>) =>
  Array.from(new Set(values.filter((value): value is string => Boolean(value))));

const buildApiBaseCandidates = () => {
  const browserHost =
    typeof window !== "undefined" && window.location.hostname
      ? window.location.hostname
      : "127.0.0.1";

  return dedupeValues([
    ENV_API_BASE,
    `http://${browserHost}:8000`,
    "http://127.0.0.1:8000",
    "http://localhost:8000",
  ]);
};

const wsBaseFromApiBase = (apiBase: string) => {
  if (ENV_WS_BASE) {
    return ENV_WS_BASE;
  }

  const url = new URL(apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/tutor";
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
};

type ArchiveSession = {
  session_id: string;
  title: string;
  grade: number;
  topic_title?: string | null;
  lesson_stage: string;
  summary: string;
  updated_at: string;
};

type SessionMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  transport?: string;
};

type SessionMeta = {
  session_id: string;
  student_id: string;
  title: string;
  board: string;
  subject: string;
  grade: number;
  topic_slug?: string | null;
  topic_title?: string | null;
  tutor_name: string;
  lesson_stage: string;
  summary: string;
  created_at: string;
  updated_at: string;
  lesson_notes: string[];
  metadata: Record<string, unknown>;
  transcript?: SessionMessage[];
};

type LessonStatePayload = {
  stage: string;
  topic_slug?: string | null;
  topic_title?: string | null;
  concept_id?: string | null;
  concept_title?: string | null;
  summary: string;
  note_cards: string[];
  whiteboard?: WhiteboardPayload | null;
   homework?: string[];
   class_duration_minutes?: number;
   chapter_label?: string;
};

type LiveAvatarStatusPayload = {
  provider: string;
  configured: boolean;
  auto_start?: boolean;
  mode?: string;
  is_sandbox?: boolean;
  language?: string;
  speech_speed?: number;
  missing_fields?: string[];
  setup_hint?: string;
  embed_url?: string;
};

type SpeechRecognitionResult = {
  transcript: string;
};

type SpeechRecognitionResultLike = ArrayLike<SpeechRecognitionResult> & {
  isFinal?: boolean;
};

type SpeechRecognitionEventLike = {
  resultIndex?: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
};

type BrowserSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  continuous?: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
};

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

type BrowserWindow = Window &
  typeof globalThis & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
    webkitAudioContext?: typeof AudioContext;
  };

const getStudentId = () => {
  const existing = window.localStorage.getItem(STUDENT_ID_KEY);
  if (existing) {
    return existing;
  }

  const next = `student-${window.crypto.randomUUID()}`;
  window.localStorage.setItem(STUDENT_ID_KEY, next);
  return next;
};

const createFreshStudentId = () => {
  const next = `student-${window.crypto.randomUUID()}`;
  window.localStorage.setItem(STUDENT_ID_KEY, next);
  return next;
};

const formatWhen = (value?: string) => {
  if (!value) {
    return "Just now";
  }

  const date = new Date(value);
  return date.toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getAudioContextConstructor = () => {
  const browserWindow = window as BrowserWindow;
  return browserWindow.AudioContext || browserWindow.webkitAudioContext;
};

const downsampleFloat32ToInt16 = (
  input: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
) => {
  if (inputSampleRate === outputSampleRate) {
    const buffer = new Int16Array(input.length);
    for (let index = 0; index < input.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, input[index] ?? 0));
      buffer[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return buffer;
  }

  const ratio = inputSampleRate / outputSampleRate;
  const length = Math.max(1, Math.round(input.length / ratio));
  const output = new Int16Array(length);

  let outputIndex = 0;
  let inputIndex = 0;
  while (outputIndex < length) {
    const nextIndex = Math.min(input.length, Math.round((outputIndex + 1) * ratio));
    let sum = 0;
    let count = 0;

    for (let cursor = inputIndex; cursor < nextIndex; cursor += 1) {
      sum += input[cursor] ?? 0;
      count += 1;
    }

    const sample = count > 0 ? sum / count : input[inputIndex] ?? 0;
    const clamped = Math.max(-1, Math.min(1, sample));
    output[outputIndex] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    outputIndex += 1;
    inputIndex = nextIndex;
  }

  return output;
};

const uint8ArrayToBase64 = (bytes: Uint8Array) => {
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return window.btoa(binary);
};

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

const toSpokenText = (value: string) =>
  value
    .replace(/\*\*/g, "")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/^[-*]\s*/gm, "")
    .replace(/^\d+\.\s*/gm, "")
    .replace(/\s+/g, " ")
    .trim();

const getPreviewText = (value: string, maxLength = 240) => {
  const spoken = toSpokenText(value);
  if (spoken.length <= maxLength) {
    return spoken;
  }
  return `${spoken.slice(0, maxLength).trimEnd()}...`;
};

export default function Chat() {
  const avatarProvider = getAvatarProviderConfig();
  const ws = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const initialGradeRef = useRef(10);
  const playbackCursorRef = useRef(0);
  const playbackTimerRef = useRef<number | null>(null);
  const autoListenTimerRef = useRef<number | null>(null);
  const inputAudioContextRef = useRef<AudioContext | null>(null);
  const inputSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const inputProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const inputSilenceRef = useRef<GainNode | null>(null);
  const inputSilenceTimerRef = useRef<number | null>(null);
  const inputSpeechDetectedRef = useRef(false);
  const inputClosingRef = useRef(false);
  const outputAudioContextRef = useRef<AudioContext | null>(null);
  const activePlaybackSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const speechTurnRequestedRef = useRef(false);
  const speechResultCapturedRef = useRef(false);
  const speechRestartTimerRef = useRef<number | null>(null);

  const [input, setInput] = useState("");
  const [grade, setGrade] = useState(10);
  const [studentId, setStudentId] = useState("");
  const [sessionMeta, setSessionMeta] = useState<SessionMeta | null>(null);
  const [archive, setArchive] = useState<ArchiveSession[]>([]);
  const [lessonState, setLessonState] = useState<LessonStatePayload | null>(null);
  const [wsStatus, setWsStatus] = useState("Offline");
  const [tutorStatus, setTutorStatus] = useState("Preparing your lesson...");
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isHandsFreeMode, setIsHandsFreeMode] = useState(true);
  const [tutorAudioMuted, setTutorAudioMuted] = useState(false);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [speechRecognitionSupported, setSpeechRecognitionSupported] = useState(false);
  const [liveAudioSupported, setLiveAudioSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isBiDiStreaming, setIsBiDiStreaming] = useState(false);
  const [liveReady, setLiveReady] = useState(false);
  const [liveConnected, setLiveConnected] = useState(false);
  const [showFullTranscript, setShowFullTranscript] = useState(false);
  const [liveAvatarStatus, setLiveAvatarStatus] = useState<LiveAvatarStatusPayload | null>(null);
  const [liveAvatarEmbedUrl, setLiveAvatarEmbedUrl] = useState<string | null>(null);
  const liveSquelchRef = useRef(false);
  const [isBootingHumanAvatar, setIsBootingHumanAvatar] = useState(false);
  const [avatarStatusRefreshKey, setAvatarStatusRefreshKey] = useState(0);
  const [wsReopenTick, setWsReopenTick] = useState(0);
  const [mounted, setMounted] = useState(false);
  const [activeApiBase, setActiveApiBase] = useState<string>(ENV_API_BASE ?? "");
  const [activeWsBase, setActiveWsBase] = useState<string>(ENV_WS_BASE ?? "");
  const [resourceTab, setResourceTab] = useState<"notes" | "homework">("notes");
  const [activeTab, setActiveTab] = useState("Homework");

  useEffect(() => {
    setMounted(true);
  }, []);

  const {
    messages,
    isStreaming,
    addUserMessage,
    hydrateMessages,
    clearMessages,
    startAssistantMessage,
    appendToAssistant,
    endStreaming,
  } = useChatStore();

  const stopLiveAudioPlayback = () => {
    activePlaybackSourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {}
      try {
        source.disconnect();
      } catch {}
    });
    activePlaybackSourcesRef.current = [];

    if (playbackTimerRef.current) {
      window.clearTimeout(playbackTimerRef.current);
      playbackTimerRef.current = null;
    }
    window.speechSynthesis?.cancel();
    playbackCursorRef.current = 0;
    setIsSpeaking(false);
  };

  const playLiveAudioChunk = useEffectEvent(async (base64Data: string, sampleRate: number) => {
    if (tutorAudioMuted || speechTurnRequestedRef.current) {
      return;
    }

    const AudioContextConstructor = getAudioContextConstructor();
    if (!AudioContextConstructor) {
      return;
    }

    if (!outputAudioContextRef.current) {
      outputAudioContextRef.current = new AudioContextConstructor();
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
      activePlaybackSourcesRef.current = activePlaybackSourcesRef.current.filter(
        (item) => item !== source
      );
    };

    const startAt = Math.max(audioContext.currentTime + 0.02, playbackCursorRef.current);
    playbackCursorRef.current = startAt + audioBuffer.duration;
    setIsSpeaking(true);
    source.start(startAt);

    if (playbackTimerRef.current) {
      window.clearTimeout(playbackTimerRef.current);
    }
    playbackTimerRef.current = window.setTimeout(() => {
      if (audioContext.currentTime >= playbackCursorRef.current - 0.05) {
        setIsSpeaking(false);
      }
    }, Math.max(120, (playbackCursorRef.current - audioContext.currentTime) * 1000 + 60));
  });

  const handleRecognizedSpeech = useEffectEvent((transcript: string) => {
    setInput(transcript);
    sendMessage(transcript);
  });

  const startStudentListening = useEffectEvent(() => {
    // Interrupt tutor audio immediately when the student starts talking.
    stopLiveAudioPlayback();
    setIsSpeaking(false);
    liveSquelchRef.current = true;
    // Don't close the websocket - we need it to send the recognized speech back to the server
    // The interruption is just stopping the playback, not closing the connection
  });

  const pauseStudentListening = () => {
    speechTurnRequestedRef.current = false;
    speechResultCapturedRef.current = false;
    if (speechRestartTimerRef.current) {
      window.clearTimeout(speechRestartTimerRef.current);
      speechRestartTimerRef.current = null;
    }
    if (autoListenTimerRef.current) {
      window.clearTimeout(autoListenTimerRef.current);
      autoListenTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
  };

  const handleInitialBootstrap = useEffectEvent((currentGrade: number) => {
    void bootstrapSession({ gradeOverride: currentGrade });
  });

  const handlePlaybackFallback = useEffectEvent(() => {
    if (liveConnected) {
      return;
    }
    speakLastMessage();
  });

  const requestBackend = useCallback(
    async (path: string, init?: RequestInit) => {
      const candidates = dedupeValues([
        ...buildApiBaseCandidates(),
        activeApiBase,
      ]);
      const errors: string[] = [];
      let lastError: Error | null = null;

      for (const base of candidates) {
        const controller = new AbortController();
        const timeoutMs = path === "/session/start" ? 30000 : 15000;
        const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
        try {
          const response = await fetch(`${base}${path}`, {
            ...init,
            signal: controller.signal,
          });
          setActiveApiBase(base);
          setActiveWsBase(wsBaseFromApiBase(base));
          window.clearTimeout(timeout);
          return response;
        } catch (error) {
          window.clearTimeout(timeout);
          if (error instanceof DOMException && error.name === "AbortError") {
            lastError = new Error(
              `Request to ${base}${path} timed out after ${timeoutMs / 1000}s.`
            );
          } else if (error instanceof Error) {
            lastError = error;
          } else {
            lastError = new Error("Could not reach the backend.");
          }
          errors.push(lastError.message);
          console.warn(`[mathverse] backend request failed for ${base}${path}:`, lastError);
        }
      }

      const suffix = errors.length ? ` Tried: ${errors.join(" | ")}` : "";
      throw lastError ?? new Error(`Could not reach the backend.${suffix}`);
    },
    [activeApiBase]
  );

  const startHumanAvatar = async () => {
    if (avatarProvider.provider !== "liveavatar" || isBootingHumanAvatar) {
      return;
    }

    setIsBootingHumanAvatar(true);
    setTutorStatus("Starting the human avatar lesson view...");

    try {
      const response = await requestBackend("/avatar/liveavatar/bootstrap", {
        method: "POST",
      });
      const data = (await response.json()) as LiveAvatarStatusPayload & {
        detail?: string;
      };
      if (!response.ok) {
        throw new Error(data.detail || "Could not start the human avatar.");
      }

      setLiveAvatarEmbedUrl(data.embed_url ?? null);
      setLiveAvatarStatus((current) => ({
        ...(current ?? {
          provider: "liveavatar",
          configured: true,
        }),
        ...data,
        configured: true,
      }));
      setTutorStatus("Human avatar is live. Ava is ready on video.");
    } catch (error) {
      setTutorStatus(
        error instanceof Error ? error.message : "Could not start the human avatar."
      );
    } finally {
      setIsBootingHumanAvatar(false);
    }
  };

  const startFreshClassroom = () => {
    const nextStudentId = createFreshStudentId();
    pauseStudentListening();
    stopLiveAudioPlayback();
    clearMessages();
    setInput("");
    setArchive([]);
    setLessonState(null);
    setSessionMeta(null);
    setLiveAvatarEmbedUrl(null);
    setTutorAudioMuted(false);
    setTutorStatus("Starting a fresh lesson...");
    void bootstrapSession({
      gradeOverride: grade,
      startNew: true,
      studentIdOverride: nextStudentId,
    });
  };

  useEffect(() => {
    setStudentId(getStudentId());
  }, []);

  useEffect(() => {
    if (avatarProvider.provider !== "liveavatar") {
      return;
    }

    const loadStatus = async () => {
      try {
        const response = await requestBackend("/avatar/liveavatar/status");
        const data = (await response.json()) as LiveAvatarStatusPayload;
        if (!response.ok) {
          throw new Error("Could not load LiveAvatar status.");
        }
        setLiveAvatarStatus(data);
      } catch {
        setLiveAvatarStatus({
          provider: "liveavatar",
          configured: false,
          setup_hint: "The LiveAvatar backend status could not be loaded.",
        });
      }
    };

    void loadStatus();
  }, [activeApiBase, avatarProvider.provider, avatarStatusRefreshKey, requestBackend]);

  useEffect(() => {
    if (
      avatarProvider.provider !== "liveavatar" ||
      !liveAvatarStatus ||
      !liveAvatarStatus.configured ||
      !liveAvatarStatus.auto_start ||
      liveAvatarEmbedUrl ||
      isBootingHumanAvatar
    ) {
      return;
    }

    void startHumanAvatar();
  }, [avatarProvider.provider, liveAvatarStatus, liveAvatarEmbedUrl, isBootingHumanAvatar]);

  useEffect(() => {
    const browserWindow = window as BrowserWindow;
    const SpeechRecognition =
      browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-IN";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => {
        startStudentListening();
      };

      recognition.onresult = (event: SpeechRecognitionEventLike) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let index = event.resultIndex ?? 0; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result?.[0]?.transcript?.trim();
          if (!transcript) {
            continue;
          }

          if (result.isFinal) {
            finalTranscript += ` ${transcript}`;
          } else {
            interimTranscript += ` ${transcript}`;
          }
        }

        const preview = interimTranscript.trim();
        if (preview) {
          stopLiveAudioPlayback();
          setInput(preview);
          setTutorStatus(`Listening: ${preview}`);
        }

        const spoken = finalTranscript.trim();
        if (spoken) {
          speechTurnRequestedRef.current = false;
          speechResultCapturedRef.current = true;
          if (speechRestartTimerRef.current) {
            window.clearTimeout(speechRestartTimerRef.current);
            speechRestartTimerRef.current = null;
          }
          setIsListening(false);
          setTutorStatus("Processing your answer...");
          handleRecognizedSpeech(spoken);
          recognition.stop();
        }
      };
      recognition.onend = () => {
        if (speechTurnRequestedRef.current && !speechResultCapturedRef.current) {
          speechRestartTimerRef.current = window.setTimeout(() => {
            if (!speechTurnRequestedRef.current) {
              return;
            }

            try {
              recognition.start();
              setIsListening(true);
              setTutorStatus("Still listening. Ask your maths question.");
            } catch {
              speechTurnRequestedRef.current = false;
              setIsListening(false);
              setTutorStatus("I could not keep listening. Please try again.");
            }
          }, 220);
          return;
        }

        setIsListening(false);
      };
      recognition.onerror = (event) => {
        const isAbort = event.error === "aborted";
        const errorMessage = event.error || "unknown error";
        
        speechTurnRequestedRef.current = false;
        speechResultCapturedRef.current = false;
        if (speechRestartTimerRef.current) {
          window.clearTimeout(speechRestartTimerRef.current);
          speechRestartTimerRef.current = null;
        }
        setIsListening(false);
        
        if (!isAbort) {
          if (errorMessage === "no-speech") {
            setTutorStatus("No speech detected. Please try again or type your answer.");
          } else if (errorMessage === "network") {
            setTutorStatus("Network error. Please check your internet connection.");
          } else if (errorMessage === "not-allowed") {
            setTutorStatus("Microphone permission denied. Enable in browser settings.");
          } else {
            setTutorStatus(`Voice error: ${errorMessage}. Please try again or type.`);
          }
        }
      };
      recognitionRef.current = recognition;
      setSpeechRecognitionSupported(true);
    }

    setLiveAudioSupported(Boolean(getAudioContextConstructor()));
  }, []);

  useEffect(() => {
    let localStream: MediaStream | null = null;

    const enableDevices = async () => {
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
        setVideoStream(localStream);
        if (videoRef.current) {
          videoRef.current.srcObject = localStream;
        }
      } catch {
        setTutorStatus("Camera and microphone are optional, but they help for live tutoring.");
      }
    };

    void enableDevices();

    return () => {
      if (localStream) {
        localStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  useEffect(() => {
    if (!studentId || sessionMeta?.student_id === studentId) {
      return;
    }

    handleInitialBootstrap(initialGradeRef.current);
  }, [sessionMeta?.student_id, studentId]);

  useEffect(() => {
    if (!studentId || !sessionMeta?.session_id) {
      return;
    }

    const socketBase =
      activeWsBase ||
      (activeApiBase
        ? wsBaseFromApiBase(activeApiBase)
        : wsBaseFromApiBase(buildApiBaseCandidates()[0]));

    const socket = new WebSocket(
      `${socketBase}?student_id=${encodeURIComponent(studentId)}&grade=${grade}&session_id=${encodeURIComponent(sessionMeta.session_id)}`
    );

    ws.current = socket;

    socket.onopen = () => {
      console.log("✅ WS OPENED");

      setWsStatus("Connected");
      setTutorStatus("Ava is starting...");

      // ✅ FIX: SEND ONLY AFTER OPEN
      socket.send(
        JSON.stringify({
          message: "ready",
          session_id: sessionMeta.session_id,
          grade: grade,
        })
      );

      console.log("🚀 READY SENT");
    };

    socket.onerror = () => {
      setWsStatus("Connection error");
      setTutorStatus("The live lesson connection needs attention.");
    };

    socket.onclose = () => {
      setWsStatus("Disconnected");
      setLiveConnected(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "session_meta") {
          setSessionMeta((current) => ({
            ...(current ?? {}),
            ...(data.session ?? {}),
          }));
          setArchive(data.archive ?? []);
          setLiveReady(Boolean(data.live_capabilities?.native_audio_ready));
          setLiveConnected(Boolean(data.live_capabilities?.native_audio_connected));
        }

        if (data.type === "history") {
          hydrateMessages(
            (data.messages ?? []).map((item: SessionMessage) => ({ ...item }))
          );
        }

        if (data.type === "state") {
          setLessonState(data.state);
          if (data.archive) {
            setArchive(data.archive);
          }
        }

        if (data.type === "live_status") {
          setTutorStatus(data.content ?? "Gemini Live connected.");
          setLiveConnected(true);
        }

        if (data.type === "live_warning" || data.type === "live_error") {
          setTutorStatus(data.content ?? "The live tutor needs attention.");
        }

        if (data.type === "transcript") {
          setInput(data.content ?? "");
          setTutorStatus(`Heard: ${data.content}`);
        }

        if (data.type === "user_turn") {
          addUserMessage(data.content, {
            timestamp: new Date().toISOString(),
            transport: data.transport ?? "bidi",
          });
          setInput("");
        }

        if (data.type === "squelch") {
          liveSquelchRef.current = true;
          stopLiveAudioPlayback();
          setIsSpeaking(false);
          return;
        }

        if (
          liveSquelchRef.current &&
          data.type !== "assistant_turn_start" &&
          data.type !== "start"
        ) {
          return;
        }

        if (data.type === "assistant_turn_start" || data.type === "start") {
          liveSquelchRef.current = false;
          pauseStudentListening();
          startAssistantMessage();
          setTutorStatus("Ava is explaining the lesson...");
        }

        if (data.type === "assistant_text" || data.type === "chunk") {
          appendToAssistant(data.content);
        }

        if (data.type === "live_audio" && data.data) {
          if (liveSquelchRef.current) return;
          void playLiveAudioChunk(data.data, data.sample_rate ?? 24000);
        }

        if (data.type === "assistant_turn_complete" || data.type === "done") {
          endStreaming();
          setTutorStatus("Ava is waiting for your next response.");

          if (data.state) {
            setLessonState(data.state);
          }

          if (data.archive) {
            setArchive(data.archive);
          }

          if (data.reason !== "interrupted") {
            handlePlaybackFallback();
          } else {
            liveSquelchRef.current = false;
            stopLiveAudioPlayback();
            setIsSpeaking(false);
          }
        }
      } catch {
        setTutorStatus("A lesson event could not be parsed.");
      }
    };

    return () => {
      socket.close();
    };
  }, [
    addUserMessage,
    activeApiBase,
    activeWsBase,
    appendToAssistant,
    endStreaming,
    grade,
    hydrateMessages,
    sessionMeta?.session_id,
    startAssistantMessage,
    studentId,
    wsReopenTick,
  ]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      window.speechSynthesis?.cancel();
      if (autoListenTimerRef.current) {
        window.clearTimeout(autoListenTimerRef.current);
        autoListenTimerRef.current = null;
      }
      if (speechRestartTimerRef.current) {
        window.clearTimeout(speechRestartTimerRef.current);
        speechRestartTimerRef.current = null;
      }
      if (inputSilenceTimerRef.current) {
        window.clearTimeout(inputSilenceTimerRef.current);
        inputSilenceTimerRef.current = null;
      }
      if (playbackTimerRef.current) {
        window.clearTimeout(playbackTimerRef.current);
        playbackTimerRef.current = null;
      }
      playbackCursorRef.current = 0;
      setIsSpeaking(false);
      void inputAudioContextRef.current?.close();
      void outputAudioContextRef.current?.close();
    };
  }, []);

  const bootstrapSession = async ({
    requestedSessionId,
    gradeOverride,
    startNew = false,
    studentIdOverride,
  }: {
    requestedSessionId?: string;
    gradeOverride?: number;
    startNew?: boolean;
    studentIdOverride?: string;
  }) => {
    const activeStudentId = studentIdOverride ?? studentId;
    if (!activeStudentId) {
      return;
    }

    const nextGrade = gradeOverride ?? grade;
    setIsBootstrapping(true);
    clearMessages();
    setLiveAvatarEmbedUrl(null);
    setTutorStatus(
      startNew
        ? "Starting a fresh lesson..."
        : requestedSessionId
          ? "Opening your saved lesson..."
          : "Loading your lesson memory..."
    );

    try {
      const response = await requestBackend("/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: activeStudentId,
          grade: nextGrade,
          session_id: requestedSessionId,
          start_new: startNew,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Could not start session");
      }

      const nextSession = data.session as SessionMeta;
      setStudentId(nextSession.student_id);
      setGrade(nextSession.grade);
      setSessionMeta(nextSession);
      setArchive(data.archive ?? []);
        setLessonState({
          stage: nextSession.lesson_stage,
          topic_slug: nextSession.topic_slug,
          topic_title: nextSession.topic_title,
          summary: nextSession.summary,
          note_cards: nextSession.lesson_notes ?? [],
          homework: Array.isArray(nextSession.metadata?.homework)
            ? nextSession.metadata.homework.filter((item): item is string => typeof item === "string")
            : [],
          class_duration_minutes:
            typeof nextSession.metadata?.class_duration_minutes === "number"
              ? nextSession.metadata.class_duration_minutes
              : 45,
          chapter_label:
            typeof nextSession.metadata?.chapter_label === "string"
              ? nextSession.metadata.chapter_label
              : "",
          whiteboard:
            nextSession.metadata?.whiteboard &&
            typeof nextSession.metadata.whiteboard === "object"
            ? (nextSession.metadata.whiteboard as WhiteboardPayload)
            : null,
        concept_id:
          typeof nextSession.metadata?.concept_id === "string"
            ? nextSession.metadata.concept_id
            : null,
        concept_title:
          typeof nextSession.metadata?.concept_title === "string"
            ? nextSession.metadata.concept_title
            : null,
      });
      hydrateMessages((nextSession.transcript ?? []).map((item) => ({ ...item })));
      setTutorStatus("Classroom ready. Ava will guide the next step.");
      setAvatarStatusRefreshKey((current) => current + 1);
    } catch (error) {
      setTutorStatus(
        error instanceof Error
          ? `${error.message} Check that the backend is running on port 8000.`
          : "Could not load the lesson."
      );
    } finally {
      setIsBootstrapping(false);
    }
  };

  const getPreferredTutorVoice = (voices: SpeechSynthesisVoice[]) => {
    if (!voices.length) {
      return null;
    }

    const englishVoices = voices.filter((voice) => /en(-|_)?/i.test(voice.lang));
    const femaleVoiceHints = /female|woman|girl|samantha|kendra|zira|susan|natalie|victoria|olivia|emma|aria|luna|amy|lucy|alloy|serena|aimee|fiona/i;
    const femaleEnglish = englishVoices.find((voice) => femaleVoiceHints.test(voice.name.toLowerCase()));

    if (femaleEnglish) {
      return femaleEnglish;
    }
    return englishVoices[0] ?? voices[0];
  };

  const buildSpeechSegments = (text: string) => {
    const normalized = text.replace(/\s+/g, " ").trim();
    if (!normalized) {
      return [];
    }

    const sentences = normalized.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [normalized];
    const segments: string[] = [];
    const maxSegmentLength = 180;
    let current = "";

    const pushWrapped = (value: string) => {
      const words = value.split(" ").filter(Boolean);
      let buffer = "";
      for (const word of words) {
        if (!buffer) {
          buffer = word;
          continue;
        }

        if (`${buffer} ${word}`.length <= maxSegmentLength) {
          buffer = `${buffer} ${word}`;
          continue;
        }

        segments.push(buffer);
        buffer = word;
      }
      if (buffer) {
        segments.push(buffer);
      }
    };

    for (const sentence of sentences) {
      const chunk = sentence.trim();
      if (!chunk) {
        continue;
      }

      if (!current) {
        if (chunk.length > maxSegmentLength) {
          pushWrapped(chunk);
          current = "";
          continue;
        }
        current = chunk;
        continue;
      }

      if (`${current} ${chunk}`.length <= maxSegmentLength) {
        current = `${current} ${chunk}`;
        continue;
      }

      segments.push(current);
      if (chunk.length > maxSegmentLength) {
        pushWrapped(chunk);
        current = "";
      } else {
        current = chunk;
      }
    }

    if (current) {
      segments.push(current);
    }

    return segments;
  };

  const speakLastMessage = () => {
    if (tutorAudioMuted || !("speechSynthesis" in window)) {
      return;
    }

    const lastMessage = useChatStore.getState().messages.at(-1);
    if (!lastMessage || lastMessage.role !== "assistant") {
      return;
    }

    const spoken = toSpokenText(lastMessage.content);
    const segments = buildSpeechSegments(spoken);
    if (!segments.length) {
      return;
    }

    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = getPreferredTutorVoice(voices);

    window.speechSynthesis.cancel();

    const pauseBetweenSegmentsMs = 300;
    let index = 0;

    const speakNext = () => {
      if (tutorAudioMuted) {
        setIsSpeaking(false);
        return;
      }
      const segment = segments[index];
      if (!segment) {
        setIsSpeaking(false);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(segment);
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.rate = 0.52;
      utterance.pitch = 0.94;
      utterance.volume = 1;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onerror = () => setIsSpeaking(false);
      utterance.onend = () => {
        index += 1;
        if (index >= segments.length) {
          setIsSpeaking(false);
          return;
        }
        window.setTimeout(speakNext, pauseBetweenSegmentsMs);
      };

      window.speechSynthesis.speak(utterance);
    };

    speakNext();
  };

  const sendMessage = (overrideText?: string) => {
    const messageText = (overrideText ?? input).trim();
    if (!messageText || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      return;
    }

    pauseStudentListening();
    addUserMessage(messageText, {
      timestamp: new Date().toISOString(),
      transport: "text",
    });

    ws.current.send(
      JSON.stringify({
        session_id: sessionMeta?.session_id,
        message: messageText,
        grade,
      })
    );

    setInput("");
    stopLiveAudioPlayback();
    setTutorStatus("Ava is thinking through your math question...");
  };

  const startListening = () => {
    if (!recognitionRef.current || isListening) {
      return;
    }

    pauseStudentListening();
    stopLiveAudioPlayback();
    
    // Request microphone permission first if not already granted
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      // Stop the stream - we just wanted to request permission
      stream.getTracks().forEach(track => track.stop());
      
      // Now start speech recognition
      speechTurnRequestedRef.current = true;
      speechResultCapturedRef.current = false;
      if (speechRestartTimerRef.current) {
        window.clearTimeout(speechRestartTimerRef.current);
        speechRestartTimerRef.current = null;
      }
      setIsListening(true);
      setTutorStatus("I am listening. Ask your maths question and pause when you finish.");
      try {
        if (recognitionRef.current) {
          recognitionRef.current.start();
        } else {
          throw new Error("Speech recognition not initialized");
        }
      } catch (err) {
        speechTurnRequestedRef.current = false;
        setIsListening(false);
        setTutorStatus("Could not start voice input. Please check microphone permissions.");
      }
    }).catch(() => {
      setTutorStatus("Microphone access denied. Please enable microphone permissions in browser settings.");
      setIsListening(false);
    });
  };

  const stopListening = () => {
    if (!recognitionRef.current || !isListening) {
      return;
    }

    pauseStudentListening();
    setTutorStatus("Voice input stopped.");
  };

  const autoStartListening = useEffectEvent(() => {
    startListening();
  });

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const readyForStudentTurn =
      isHandsFreeMode &&
      speechRecognitionSupported &&
      Boolean(sessionMeta?.session_id) &&
      wsStatus === "Connected" &&
      !isBootstrapping &&
      !isStreaming &&
      !isSpeaking &&
      !isListening &&
      lastMessage?.role === "assistant";

    if (!readyForStudentTurn) {
      if (autoListenTimerRef.current) {
        window.clearTimeout(autoListenTimerRef.current);
        autoListenTimerRef.current = null;
      }
      return;
    }

    autoListenTimerRef.current = window.setTimeout(() => {
      autoStartListening();
    }, 900);

    return () => {
      if (autoListenTimerRef.current) {
        window.clearTimeout(autoListenTimerRef.current);
        autoListenTimerRef.current = null;
      }
    };
  }, [
    isBootstrapping,
    isHandsFreeMode,
    isListening,
    isSpeaking,
    isStreaming,
    messages,
    sessionMeta?.session_id,
    speechRecognitionSupported,
    wsStatus,
  ]);

  const finishBiDiTurn = (status = "Sending your question to Ava...") => {
    if (inputClosingRef.current) {
      return;
    }

    inputClosingRef.current = true;

    if (inputSilenceTimerRef.current) {
      window.clearTimeout(inputSilenceTimerRef.current);
      inputSilenceTimerRef.current = null;
    }

    inputProcessorRef.current?.disconnect();
    inputSourceRef.current?.disconnect();
    inputSilenceRef.current?.disconnect();
    inputProcessorRef.current = null;
    inputSourceRef.current = null;
    inputSilenceRef.current = null;

    if (inputAudioContextRef.current) {
      void inputAudioContextRef.current.close();
      inputAudioContextRef.current = null;
    }

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "audio_stream_end" }));
    }

    inputSpeechDetectedRef.current = false;
    setIsBiDiStreaming(false);
    setTutorStatus(status);
    inputClosingRef.current = false;
  };

  const startBiDiStreaming = async () => {
    if (!liveConnected || !liveAudioSupported || !ws.current) {
      setTutorStatus("Gemini Live audio is not ready yet.");
      return;
    }

    const AudioContextConstructor = getAudioContextConstructor();
    if (!AudioContextConstructor) {
      setTutorStatus("Web Audio is not available in this browser.");
      return;
    }

    let stream = videoStream;
    if (!stream || stream.getAudioTracks().length === 0) {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setVideoStream(stream);
      } catch {
        setTutorStatus("Microphone input is not available for the live channel.");
        return;
      }
    }

    stopLiveAudioPlayback();
    const audioContext = new AudioContextConstructor();
    await audioContext.resume();
    inputSpeechDetectedRef.current = false;
    inputClosingRef.current = false;

    if (inputSilenceTimerRef.current) {
      window.clearTimeout(inputSilenceTimerRef.current);
      inputSilenceTimerRef.current = null;
    }

    const sourceNode = audioContext.createMediaStreamSource(
      new MediaStream(stream.getAudioTracks())
    );
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    const silence = audioContext.createGain();
    silence.gain.value = 0;

    processor.onaudioprocess = (event) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        return;
      }

      const inputData = event.inputBuffer.getChannelData(0);
      let energy = 0;
      for (let index = 0; index < inputData.length; index += 1) {
        const sample = inputData[index] ?? 0;
        energy += sample * sample;
      }
      const rms = Math.sqrt(energy / Math.max(1, inputData.length));

      if (rms > 0.012 && !inputSpeechDetectedRef.current) {
        // First detection of student voice: hard interrupt tutor audio.
        inputSpeechDetectedRef.current = true;
        liveSquelchRef.current = true;
        stopLiveAudioPlayback();
        if (ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: "interrupt" }));
        }
      }

      const pcm = downsampleFloat32ToInt16(
        inputData,
        audioContext.sampleRate,
        LIVE_INPUT_SAMPLE_RATE
      );
      ws.current.send(
        JSON.stringify({
          type: "live_input_audio",
          data: uint8ArrayToBase64(new Uint8Array(pcm.buffer)),
          sample_rate: LIVE_INPUT_SAMPLE_RATE,
        })
      );

      if (rms > 0.016) {
        inputSpeechDetectedRef.current = true;
        if (inputSilenceTimerRef.current) {
          window.clearTimeout(inputSilenceTimerRef.current);
        }
        inputSilenceTimerRef.current = window.setTimeout(() => {
          finishBiDiTurn("Ava is listening and preparing a reply...");
        }, 1200);
      }
    };

    sourceNode.connect(processor);
    processor.connect(silence);
    silence.connect(audioContext.destination);

    inputAudioContextRef.current = audioContext;
    inputSourceRef.current = sourceNode;
    inputProcessorRef.current = processor;
    inputSilenceRef.current = silence;
    setIsBiDiStreaming(true);
    setTutorStatus("Your turn. Speak naturally, then pause for Ava to answer.");
  };

  const stopBiDiStreaming = () => {
    finishBiDiTurn("Live mic channel is off.");
  };

  const quickPrompt = (prompt: string) => {
    setInput("");
    sendMessage(prompt);
  };

  const selectArchiveSession = (session: ArchiveSession) => {
    void bootstrapSession({
      requestedSessionId: session.session_id,
      gradeOverride: session.grade,
    });
  };

  const visibleNotes =
    lessonState?.note_cards?.length
      ? lessonState.note_cards
      : sessionMeta?.lesson_notes?.length
        ? sessionMeta.lesson_notes
        : [
            "Your class notes will appear here as Ava explains the concept.",
            "Every session is saved so you can revisit it later.",
          ];
  const visibleHomework =
    lessonState?.homework?.length
      ? lessonState.homework
      : Array.isArray(sessionMeta?.metadata?.homework)
        ? sessionMeta.metadata.homework.filter((item): item is string => typeof item === "string")
        : [
            "Homework will appear here when Ava finishes the class.",
            "Each class ends with 2-3 NCERT homework questions.",
          ];
  const classDurationMinutes =
    lessonState?.class_duration_minutes ??
    (typeof sessionMeta?.metadata?.class_duration_minutes === "number"
      ? sessionMeta.metadata.class_duration_minutes
      : 45);
  const chapterLabel =
    lessonState?.chapter_label ||
    (typeof sessionMeta?.metadata?.chapter_label === "string"
      ? sessionMeta.metadata.chapter_label
      : "Chapter sequence");

  const visibleTranscriptMessages = showFullTranscript ? messages : messages.slice(-4);
  const hiddenTurnCount = Math.max(0, messages.length - visibleTranscriptMessages.length);
  const latestTeacherMessage =
    [...messages].reverse().find((message) => message.role === "assistant") ?? null;
  const isTeacherNarrating = isSpeaking || isStreaming;
  const isFocusScreen = !showFullTranscript;
  const currentWhiteboard =
    lessonState?.whiteboard ??
    ((sessionMeta?.metadata?.whiteboard as WhiteboardPayload | undefined) ?? null);
  const avatarProviderLabel =
    mounted && avatarProvider.provider === "liveavatar" && liveAvatarStatus?.configured
      ? liveAvatarEmbedUrl
        ? "LiveAvatar Human Video"
        : "LiveAvatar Ready"
      : null;
  const avatarSetupHint =
    mounted && avatarProvider.provider === "liveavatar" ? liveAvatarStatus?.setup_hint : undefined;

  return (
    <div className="h-screen w-full bg-white p-4 flex flex-col gap-4">

      {/* TOP HEADER */}
      <div className="border p-3 flex justify-between items-center">
        <div>
          <div className="font-semibold">Standard / Grade: {grade}</div>
          <div>Student Name: {studentId || "Student"}</div>
        </div>

        {/* TABS */}
        <div className="flex gap-4">
          {["Homework", "Feed", "MindMap"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`border px-4 py-2 ${
                activeTab === tab ? "bg-black text-white" : ""
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* MAIN GRID */}
      <div className="flex flex-1 gap-4">

        {/* LEFT: LIVE HUMAN */}
        <div className="w-[25%] border flex items-center justify-center">
          <div className="text-center">
            <div className="mb-2 font-semibold">Live Human</div>

            <TeacherAvatar
              name="Ava"
              isSpeaking={isSpeaking}
              videoRef={videoRef}
              videoStream={null}
              mounted
            />
          </div>
        </div>

        {/* CENTER: WHITEBOARD */}
        <div className="w-[50%] border p-4 flex flex-col">

          <div className="mb-2">
            <div>Chapter No: {lessonState?.chapter_label || "-"}</div>
            <div>Topic Name: {lessonState?.topic || "-"}</div>
          </div>

          <div className="flex-1 border flex items-center justify-center">
            <ClassWhiteboard
              boardSegments={lessonState?.board_segments || []}
              isNarrating={isStreaming}
              isFocusStage
            />
          </div>
        </div>

        {/* RIGHT: TAB CONTENT */}
        <div className="w-[25%] border p-3">

          {activeTab === "Homework" && (
            <div>
              <h3 className="font-semibold mb-2">Homework</h3>
              <div>{lessonState?.homework || "No homework yet"}</div>
            </div>
          )}

          {activeTab === "Feed" && (
            <div>
              <h3 className="font-semibold mb-2">Feed</h3>
              <div className="text-sm whitespace-pre-wrap">
                {messages.map((m, i) => (
                  <div key={i}>{m.content}</div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "MindMap" && (
            <div>
              <h3 className="font-semibold mb-2">Mind Maps / Notes</h3>
              <div>{lessonState?.notes || "No notes yet"}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};