"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ClassResponse, ExamMode, TeachingLanguage, TutorPayload } from "../services/api";
import { startClassStream } from "../services/tutorStream";
import { playVoiceStream, type VoiceController } from "../services/voice";

type Args = {
  sessionId: string;
  examMode: ExamMode;
  teachingLanguage: TeachingLanguage;
  onResponse?: (response: ClassResponse) => void;
};

export function useTutorStream({ sessionId, examMode, teachingLanguage, onResponse }: Args) {
  const [response, setResponse] = useState<ClassResponse | null>(null);
  const [visibleSteps, setVisibleSteps] = useState<string[]>([]);
  const [activeStepIndex, setActiveStepIndex] = useState<number | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const voiceRef = useRef<VoiceController | null>(null);
  const autoTimerRef = useRef<number | null>(null);
  const lastGradeRef = useRef<number | undefined>(undefined);
  const lastSubjectRef = useRef<string | undefined>(undefined);
  const silentRetryRef = useRef(0);

  const stop = useCallback(() => {
    voiceRef.current?.stop();
    if (autoTimerRef.current) window.clearTimeout(autoTimerRef.current);
    setActiveStepIndex(null);
  }, []);

  const prime = useCallback(
    (nextResponse: ClassResponse) => {
      stop();
      const whiteboard = nextResponse.whiteboard || nextResponse.content?.whiteboard;
      const steps =
        nextResponse.steps?.length
          ? nextResponse.steps
          : nextResponse.content?.steps?.length
            ? nextResponse.content.steps
            : whiteboard?.solution_steps?.length
              ? whiteboard.solution_steps
              : [...(whiteboard?.equations || []), ...(whiteboard?.chalk_lines || [])];

      setResponse(nextResponse);
      setVisibleSteps(steps);
      setActiveStepIndex(null);
      setIsSpeaking(false);
      setPaused(false);
      setLoading(false);
      setError(null);
    },
    [stop],
  );

  const start = useCallback(
    async (
      input: TutorPayload["input"] & { grade?: number; subject?: string } = { action: "start", grade: 10, subject: "math" },
      options?: { silent?: boolean },
    ) => {
      stop();
      if (!options?.silent) {
        setLoading(true);
      }
      setError(null);
      setPaused(false);
      setVisibleSteps([]);
      setActiveStepIndex(null);
      lastGradeRef.current = typeof input.grade === "number" ? input.grade : lastGradeRef.current;
      lastSubjectRef.current = typeof input.subject === "string" ? input.subject : lastSubjectRef.current;
      const isAutoContinueTurn = options?.silent && String(input.action || "").toLowerCase() === "continue";

      try {
        const requestedGrade = typeof input.grade === "number" ? input.grade : undefined;
        const stream = await startClassStream({
          session_id: sessionId,
          input,
          context: {
            exam: examMode,
            grade: requestedGrade,
            teaching_language: teachingLanguage,
          },
        });
        silentRetryRef.current = 0;

        setResponse(stream.response);
        setVisibleSteps(stream.steps);
        onResponse?.(stream.response);

        const avatarVoice = stream.response.avatar_voice || stream.response.content?.avatar_voice;
        const paceLabel = String(avatarVoice?.pace || "").toLowerCase();
        const voiceRate =
          paceLabel.includes("slow")
            ? 0.82
            : paceLabel.includes("short") || paceLabel.includes("fast")
              ? 1.0
              : paceLabel.includes("steady") || paceLabel.includes("normal")
                ? 0.95
                : 0.9;
        const pauseMs =
          typeof avatarVoice?.pause_ms === "number"
            ? Math.max(120, avatarVoice.pause_ms)
            : paceLabel.includes("slow")
              ? 320
              : 180;

        const totalSteps = stream.steps.length;
        const totalChunks = Math.max(1, stream.voice_chunks.length);
        voiceRef.current = playVoiceStream(stream.voice_chunks.join(". "), {
          chunks: stream.voice_chunks,
          rate: voiceRate,
          pauseMs,
          onStart: () => setIsSpeaking(true),
          onChunkStart: (chunkIndex) => {
            if (!totalSteps) return;
            const mappedIndex = Math.min(
              totalSteps - 1,
              Math.floor((chunkIndex * totalSteps) / totalChunks),
            );
            setActiveStepIndex(mappedIndex);
          },
          onEnd: () => {
            setIsSpeaking(false);
            setActiveStepIndex(null);
          },
        });
      } catch (err) {
        if (options?.silent) {
          if (silentRetryRef.current < 2) {
            const retryAttempt = silentRetryRef.current + 1;
            silentRetryRef.current = retryAttempt;
            autoTimerRef.current = window.setTimeout(
              () =>
                void start(
                  {
                    action: "continue",
                    grade: lastGradeRef.current,
                    subject: lastSubjectRef.current || "math",
                  },
                  { silent: true },
                ),
              900 * retryAttempt,
            );
          }
        } else {
          setError(err instanceof Error ? err.message : "Unable to start class stream");
        }
      } finally {
        if (!options?.silent) {
          setLoading(false);
        }
      }
    },
    [examMode, onResponse, sessionId, stop, teachingLanguage],
  );

  const pauseOrResume = useCallback(() => {
    if (!voiceRef.current) return;
    if (paused) {
      voiceRef.current.resume();
      setIsSpeaking(true);
      setPaused(false);
    } else {
      voiceRef.current.pause();
      setIsSpeaking(false);
      setPaused(true);
    }
  }, [paused]);

  useEffect(() => stop, [stop]);

  return {
    response,
    visibleSteps,
    activeStepIndex,
    isSpeaking,
    loading,
    error,
    paused,
    start,
    pauseOrResume,
    stop,
    prime,
  };
}
