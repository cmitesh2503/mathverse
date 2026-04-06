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
  const [tutorStatus, setTutorStatus] = useState("Preparing your classroom...");
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
      const candidates = dedupeValues([activeApiBase, ...buildApiBaseCandidates()]);
      const errors: string[] = [];
      let lastError: Error | null = null;

      for (const base of candidates) {
        const controller = new AbortController();
        const timeoutMs = 15000;
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
    setTutorStatus("Starting the human avatar classroom...");

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
    setTutorStatus("Starting a fresh classroom...");
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
      (activeApiBase ? wsBaseFromApiBase(activeApiBase) : wsBaseFromApiBase(buildApiBaseCandidates()[0]));

    const socket = new WebSocket(
      `${socketBase}?student_id=${encodeURIComponent(studentId)}&grade=${grade}&session_id=${encodeURIComponent(sessionMeta.session_id)}`
    );
    ws.current = socket;

    socket.onopen = () => {
      setWsStatus("Connected");
      setTutorStatus("Ava is live and ready to teach.");
    };

    socket.onerror = () => {
      setWsStatus("Connection error");
      setTutorStatus("The live classroom connection needs attention.");
    };

    socket.onclose = () => {
      setWsStatus("Disconnected");
      setLiveConnected(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "session_meta") {
          setSessionMeta((current) => ({ ...(current ?? {}), ...(data.session ?? {}) }));
          setArchive(data.archive ?? []);
          setLiveReady(Boolean(data.live_capabilities?.native_audio_ready));
          setLiveConnected(Boolean(data.live_capabilities?.native_audio_connected));
        }

        if (data.type === "history") {
          hydrateMessages((data.messages ?? []).map((item: SessionMessage) => ({ ...item })));
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

        if (liveSquelchRef.current && data.type !== "assistant_turn_start" && data.type !== "start") {
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
          if (liveSquelchRef.current) {
            return;
          }
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
        setTutorStatus("A classroom event could not be parsed.");
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
        ? "Starting a fresh classroom..."
        : requestedSessionId
          ? "Opening your saved classroom..."
          : "Loading your classroom memory..."
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
          : "Could not load the classroom."
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

  const speakLastMessage = () => {
    if (tutorAudioMuted || !("speechSynthesis" in window)) {
      return;
    }

    const lastMessage = useChatStore.getState().messages.at(-1);
    if (!lastMessage || lastMessage.role !== "assistant") {
      return;
    }

    const utterance = new SpeechSynthesisUtterance(toSpokenText(lastMessage.content));
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = getPreferredTutorVoice(voices);

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.rate = 0.64;
    utterance.pitch = 0.94;
    utterance.volume = 1;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
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
    <div className="min-h-screen bg-[linear-gradient(180deg,#f7f2e8_0%,#efe6d3_46%,#f8f5ef_100%)] text-slate-900">
      {isFocusScreen ? (
        <div className="mx-auto max-w-[1720px] p-4 md:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-end gap-2">
            {mounted && avatarProvider.provider === "liveavatar" && (
              <button
                onClick={() => void startHumanAvatar()}
                disabled={
                  isBootingHumanAvatar || !liveAvatarStatus?.configured || !sessionMeta?.session_id
                }
                className={`rounded-full px-4 py-2 text-xs font-semibold ${
                  liveAvatarEmbedUrl ? "bg-sky-50 text-sky-800" : "bg-sky-100 text-sky-900"
                } ${
                  isBootingHumanAvatar || !liveAvatarStatus?.configured || !sessionMeta?.session_id
                    ? "cursor-not-allowed opacity-40"
                    : ""
                }`}
              >
                {isBootingHumanAvatar
                  ? "Starting Human Avatar..."
                  : liveAvatarEmbedUrl
                    ? "Restart Human Avatar"
                    : "Start Human Avatar"}
              </button>
            )}
            <button
              onClick={() => setShowFullTranscript(true)}
              className="rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900 transition hover:bg-amber-100"
            >
              Open Classroom
            </button>
            <button
              onClick={startFreshClassroom}
              className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-900 transition hover:bg-rose-100"
            >
              Fresh Classroom
            </button>
          </div>

          <div className="grid min-h-[calc(100vh-7rem)] gap-6 xl:grid-cols-[minmax(460px,0.84fr)_minmax(0,1.28fr)]">
            <TeacherAvatar
              avatarIframeUrl={liveAvatarEmbedUrl}
              avatarLaunchUrl={liveAvatarEmbedUrl}
              avatarProviderLabel={avatarProviderLabel}
              avatarSetupHint={avatarSetupHint}
              isSpeaking={isSpeaking}
              liveReady={liveConnected}
              mounted={mounted}
              name={sessionMeta?.tutor_name ?? "Ava"}
              stageMode="focus"
              status={tutorStatus}
              chapter={lessonState?.topic_title || sessionMeta?.topic_title || "CBSE mathematics"}
              summary={lessonState?.summary || sessionMeta?.summary || "Preparing the class."}
              videoRef={videoRef}
              videoStream={videoStream}
            />

            <ClassWhiteboard
              key={JSON.stringify(currentWhiteboard)}
              isNarrating={isTeacherNarrating}
              stageMode="focus"
              whiteboard={currentWhiteboard}
            />
          </div>
        </div>
      ) : (
      <div className="mx-auto max-w-7xl p-4 md:p-6">
        <div className="mb-6 flex flex-col gap-4 rounded-[2rem] border border-white/60 bg-white/70 p-5 shadow-[0_30px_120px_rgba(79,55,27,0.12)] backdrop-blur xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-700">
              MathVerse Classroom
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">
              Real-time CBSE Mathematics Tutor
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Ava keeps lesson memory, saves class notes, and lets students reopen past classes from the archive.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-slate-700">
              Grade
              <select
                value={grade}
                onChange={(event) => {
                  const nextGrade = Number(event.target.value);
                  setGrade(nextGrade);
                  void bootstrapSession({ gradeOverride: nextGrade });
                }}
                className="ml-2 bg-transparent font-semibold outline-none"
              >
                {[9, 10].map((level) => (
                  <option key={level} value={level}>
                    Class {level}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={() => void bootstrapSession({ gradeOverride: grade, startNew: true })}
              className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              Start New Class
            </button>
            <button
              onClick={startFreshClassroom}
              className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-900 transition hover:bg-rose-100"
            >
              Fresh Classroom
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <div className="rounded-[1.75rem] border border-white/60 bg-white/75 p-4 shadow-[0_24px_70px_rgba(52,36,21,0.12)] backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                Student Memory
              </div>
              <div className="mt-3 rounded-2xl bg-slate-900 px-4 py-3 text-sm text-slate-100">
                <div className="font-semibold">{studentId || "..."}</div>
                <div className="mt-1 text-xs text-slate-300">
                  Lessons are saved and can be resumed later.
                </div>
              </div>
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2 text-sm">
                  <span>Board</span>
                  <span className="font-semibold">CBSE</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                  <span>Subject</span>
                  <span className="font-semibold">Mathematics</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm">
                  <span>Live classroom</span>
                  <span className="font-semibold">{wsStatus}</span>
                </div>
              </div>
            </div>

            <div className="rounded-[1.75rem] border border-white/60 bg-white/75 p-4 shadow-[0_24px_70px_rgba(52,36,21,0.12)] backdrop-blur">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                  Class Archive
                </div>
                <div className="text-xs text-slate-500">{archive.length} saved</div>
              </div>

              <div className="mt-4 space-y-3">
                {archive.length === 0 && (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-3 py-4 text-sm text-slate-500">
                    Your saved classes will show up here.
                  </div>
                )}

                {archive.map((item) => (
                  <button
                    key={item.session_id}
                    onClick={() => selectArchiveSession(item)}
                    className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                      sessionMeta?.session_id === item.session_id
                        ? "border-amber-300 bg-amber-50"
                        : "border-slate-200 bg-slate-50 hover:border-amber-200 hover:bg-white"
                    }`}
                  >
                    <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {item.topic_title || "Math lesson"} - {formatWhen(item.updated_at)}
                    </div>
                    <div className="mt-2 text-xs text-slate-600">{item.summary}</div>
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <main className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_360px]">
            <section className="rounded-[2rem] border border-white/60 bg-white/75 p-4 shadow-[0_28px_100px_rgba(52,36,21,0.13)] backdrop-blur md:p-5">
              <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
                <TeacherAvatar
                  avatarIframeUrl={liveAvatarEmbedUrl}
                  avatarLaunchUrl={liveAvatarEmbedUrl}
                  avatarProviderLabel={avatarProviderLabel}
                  avatarSetupHint={avatarSetupHint}
                  isSpeaking={isSpeaking}
                  liveReady={liveConnected}
                  mounted={mounted}
                  name={sessionMeta?.tutor_name ?? "Ava"}
                  stageMode="default"
                  status={tutorStatus}
                  chapter={
                    lessonState?.topic_title || sessionMeta?.topic_title || "CBSE mathematics"
                  }
                  summary={lessonState?.summary || sessionMeta?.summary || "Preparing the class."}
                  videoRef={videoRef}
                  videoStream={videoStream}
                />

                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <button
                      onClick={() => quickPrompt("ready")}
                      className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-left"
                    >
                      <div className="font-semibold">Start Guided Lesson</div>
                      <div className="mt-1 text-sm text-slate-600">Let Ava teach in classroom mode.</div>
                    </button>
                    <button
                      onClick={() => quickPrompt("practice")}
                      className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-left"
                    >
                      <div className="font-semibold">Give Me Practice</div>
                      <div className="mt-1 text-sm text-slate-600">Jump into guided problem solving.</div>
                    </button>
                    <button
                      onClick={() => quickPrompt("revise last class")}
                      className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-left"
                    >
                      <div className="font-semibold">Revise Last Class</div>
                      <div className="mt-1 text-sm text-slate-600">Pull memory forward from saved sessions.</div>
                    </button>
                    <button
                      onClick={() =>
                        quickPrompt(
                          `Teach me ${sessionMeta?.topic_title || "the current chapter"} from the basics.`
                        )
                      }
                      className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-left"
                    >
                      <div className="font-semibold">Teach From Basics</div>
                      <div className="mt-1 text-sm text-slate-600">Rebuild the concept slowly.</div>
                    </button>
                  </div>

                  <ClassWhiteboard
                    key={JSON.stringify(currentWhiteboard)}
                    isNarrating={isTeacherNarrating}
                    stageMode="default"
                    whiteboard={currentWhiteboard}
                  />

                  <div className="rounded-[1.6rem] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#fbfaf7_100%)] p-3">
                    <div className="flex items-center justify-between border-b border-slate-200 px-2 pb-3">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                          Classroom Feed
                        </div>
                        <div className="mt-1 text-sm text-slate-500">
                          {showFullTranscript
                            ? isBootstrapping
                              ? "Loading session..."
                              : sessionMeta?.title || "No session yet"
                            : "Focused view with the latest teacher and student turns."}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
                          {messages.length} turns
                        </div>
                        <button
                          onClick={() => setShowFullTranscript((current) => !current)}
                          className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800"
                        >
                          {showFullTranscript ? "Focus Screen" : "Open Classroom"}
                        </button>
                      </div>
                    </div>

                    {!showFullTranscript && latestTeacherMessage && (
                      <div className="mt-3 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-700">
                          Teacher Recap
                        </div>
                        <div className="mt-2 text-sm leading-6 text-slate-700">
                          {getPreviewText(latestTeacherMessage.content, 260)}
                        </div>
                      </div>
                    )}

                    {!showFullTranscript && hiddenTurnCount > 0 && (
                      <div className="mt-3 px-2 text-xs font-medium text-slate-500">
                        Showing the latest 4 turns. Open full transcript any time.
                      </div>
                    )}

                    <div
                      className={`mt-3 space-y-4 px-1 ${
                        showFullTranscript
                          ? "h-[360px] overflow-y-auto"
                          : "max-h-[160px] overflow-hidden"
                      }`}
                    >
                      {messages.length === 0 && (
                        <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                          Ava will begin with a lesson introduction as soon as the live session opens.
                        </div>
                      )}

                      {visibleTranscriptMessages.map((msg, index) => (
                        <div
                          key={`${msg.role}-${index}-${msg.timestamp ?? "now"}`}
                          className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}
                        >
                          <div
                            className={`max-w-[88%] rounded-[1.4rem] px-4 py-3 shadow-sm ${
                              msg.role === "user"
                                ? "bg-slate-900 text-white"
                                : "border border-amber-100 bg-amber-50 text-slate-800"
                            }`}
                          >
                            <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
                              <span>{msg.role === "user" ? "Student" : sessionMeta?.tutor_name || "Tutor"}</span>
                              {showFullTranscript && msg.transport && <span>{msg.transport}</span>}
                            </div>
                            {msg.role === "assistant" ? (
                              showFullTranscript ? (
                                <div className="prose prose-sm max-w-none prose-p:my-2 prose-li:my-1">
                                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>
                              ) : (
                                <div className="text-sm leading-6 text-slate-700">
                                  {getPreviewText(msg.content, 220)}
                                </div>
                              )
                            ) : (
                              <div className="whitespace-pre-wrap text-sm leading-6">
                                {showFullTranscript ? msg.content : getPreviewText(msg.content, 160)}
                              </div>
                            )}
                            {showFullTranscript && msg.timestamp && (
                              <div className="mt-2 text-[11px] opacity-65">{formatWhen(msg.timestamp)}</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-[1.6rem] border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
                      <div className="rounded-full bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
                        Tutor voice enabled
                      </div>
                      <button
                        onClick={() => {
                          const next = !isHandsFreeMode;
                          setIsHandsFreeMode(next);
                          if (!next) {
                            pauseStudentListening();
                            setTutorStatus("Hands-free classroom mode is off.");
                          } else {
                            setTutorStatus("Hands-free classroom mode is on.");
                          }
                        }}
                        className={`rounded-full px-3 py-2 text-xs font-semibold ${
                          isHandsFreeMode
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {isHandsFreeMode ? "Hands-free On" : "Hands-free Off"}
                      </button>
                      {speechRecognitionSupported ? (
                        <button
                          onClick={isListening ? stopListening : startListening}
                          disabled={isBiDiStreaming}
                          className={`rounded-full px-3 py-2 text-xs font-semibold text-white ${
                            isListening ? "bg-rose-600" : "bg-amber-600"
                          } ${isBiDiStreaming ? "cursor-not-allowed opacity-40" : ""}`}
                        >
                          {isListening ? "Stop Listening" : "Listen Now"}
                        </button>
                      ) : (
                        <div className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-500">
                          Browser speech input unavailable
                        </div>
                      )}
                      <button
                        onClick={isBiDiStreaming ? stopBiDiStreaming : () => void startBiDiStreaming()}
                        disabled={!liveConnected || !liveAudioSupported}
                        className={`rounded-full px-3 py-2 text-xs font-semibold ${
                          isBiDiStreaming ? "bg-violet-50 text-violet-700" : "bg-violet-100 text-violet-800"
                        } ${!liveConnected || !liveAudioSupported ? "cursor-not-allowed opacity-40" : ""}`}
                      >
                        {isBiDiStreaming ? "Stop Live Mic Beta" : "Live Mic Beta"}
                      </button>
                      {avatarProvider.provider === "liveavatar" && (
                        <button
                          onClick={() => void startHumanAvatar()}
                          disabled={
                            isBootingHumanAvatar ||
                            !liveAvatarStatus?.configured ||
                            !sessionMeta?.session_id
                          }
                          className={`rounded-full px-3 py-2 text-xs font-semibold ${
                            liveAvatarEmbedUrl
                              ? "bg-sky-50 text-sky-800"
                              : "bg-sky-100 text-sky-900"
                          } ${
                            isBootingHumanAvatar || !liveAvatarStatus?.configured || !sessionMeta?.session_id
                              ? "cursor-not-allowed opacity-40"
                              : ""
                          }`}
                        >
                          {isBootingHumanAvatar
                            ? "Starting Human Avatar..."
                            : liveAvatarEmbedUrl
                              ? "Restart Human Avatar"
                              : "Start Human Avatar"}
                        </button>
                      )}
                    </div>

                    <div className="mt-3 flex gap-2">
                      <input
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            sendMessage();
                          }
                        }}
                        placeholder="Ask a math doubt, request practice, or switch chapters..."
                        className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-amber-300 focus:bg-white"
                      />
                      <button
                        onClick={() => sendMessage()}
                        className="rounded-2xl bg-amber-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-amber-700"
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <aside className="space-y-4">
              <div className="rounded-[1.75rem] border border-white/60 bg-white/80 p-4 shadow-[0_24px_70px_rgba(52,36,21,0.12)] backdrop-blur">
                <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                  Lesson Snapshot
                </div>
                <div className="mt-4 grid gap-3">
                  <div className="rounded-2xl bg-slate-900 p-4 text-white">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-300">
                      Current Chapter
                    </div>
                    <div className="mt-2 text-xl font-semibold">
                      {lessonState?.topic_title || sessionMeta?.topic_title || "Loading..."}
                    </div>
                    <div className="mt-2 text-sm text-slate-300">
                      {lessonState?.summary || sessionMeta?.summary || "Ava is preparing the lesson."}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Lesson Stage</div>
                      <div className="mt-2 font-semibold text-slate-900">
                        {lessonState?.stage || sessionMeta?.lesson_stage || "INTRO"}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Concept Focus</div>
                      <div className="mt-2 font-semibold text-slate-900">
                        {lessonState?.concept_title || "Guided lesson"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/60 bg-white/80 p-4 shadow-[0_24px_70px_rgba(52,36,21,0.12)] backdrop-blur">
                <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                  Class Notes
                </div>
                <div className="mt-4 space-y-3">
                  {visibleNotes.map((note, index) => (
                    <div
                      key={`${note}-${index}`}
                      className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-3 text-sm text-slate-700"
                    >
                      {note}
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/60 bg-white/80 p-4 shadow-[0_24px_70px_rgba(52,36,21,0.12)] backdrop-blur">
                <div className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-700">
                  Live Capabilities
                </div>
                <div className="mt-4 space-y-3 text-sm text-slate-600">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <span className="font-semibold text-slate-900">Persistent memory:</span> every session is saved with transcript and lesson notes.
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <span className="font-semibold text-slate-900">Tutor persona:</span> Ava stays in guided CBSE math-teacher mode.
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <span className="font-semibold text-slate-900">Native Gemini audio:</span>{" "}
                    {liveConnected
                      ? "bi-directional audio session is connected"
                      : liveReady
                        ? "SDK available, waiting for live session"
                        : "backend will use text stream fallback"}
                  </div>
                  {mounted && avatarProvider.provider === "liveavatar" && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                      <span className="font-semibold text-slate-900">Human avatar:</span>{" "}
                      {liveAvatarEmbedUrl
                        ? "LiveAvatar session started in the classroom"
                        : liveAvatarStatus?.configured
                          ? liveAvatarStatus.is_sandbox
                            ? "LiveAvatar is configured in sandbox mode and ready to launch"
                            : "LiveAvatar is configured and ready to launch"
                          : liveAvatarStatus?.missing_fields?.length
                            ? `missing ${liveAvatarStatus.missing_fields.join(", ")}`
                            : "LiveAvatar backend is not configured yet"}
                    </div>
                  )}
                </div>
              </div>
            </aside>
          </main>
        </div>
      </div>
      )}
    </div>
  );
}
