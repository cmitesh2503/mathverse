"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ClassResponse, ExamMode, TutorPayload } from "../services/api";
import { startClassStream } from "../services/tutorStream";
import { playVoiceStream, type VoiceController } from "../services/voice";

type Args = {
  sessionId: string;
  examMode: ExamMode;
  onResponse?: (response: ClassResponse) => void;
};

export function useTutorStream({ sessionId, examMode, onResponse }: Args) {
  const [response, setResponse] = useState<ClassResponse | null>(null);
  const [visibleSteps, setVisibleSteps] = useState<string[]>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const voiceRef = useRef<VoiceController | null>(null);
  const autoTimerRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    voiceRef.current?.stop();
    if (autoTimerRef.current) window.clearTimeout(autoTimerRef.current);
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
      setIsSpeaking(false);
      setPaused(false);
      setLoading(false);
      setError(null);
    },
    [stop],
  );

  const start = useCallback(
    async (
      input: TutorPayload["input"] & { grade?: number; subject?: string } = { grade: 9, subject: "math" },
    ) => {
      stop();
      setLoading(true);
      setError(null);
      setVisibleSteps([]);
      setPaused(false);

      try {
        const stream = await startClassStream({
          session_id: sessionId,
          input,
          context: { exam: examMode },
        });

        setResponse(stream.response);
        onResponse?.(stream.response);

        voiceRef.current = playVoiceStream(stream.voice_chunks.join(". "), {
          chunks: stream.voice_chunks,
          onStart: () => setIsSpeaking(true),
          onChunkStart: (index) => {
            const nextStep = stream.steps[index];
            if (nextStep) {
              window.setTimeout(() => {
                setVisibleSteps((current) => (current.includes(nextStep) ? current : [...current, nextStep]));
              }, 1200);
            }
          },
          onEnd: () => {
            setVisibleSteps(stream.steps);
            setIsSpeaking(false);
            if (stream.response.type === "teach" && stream.response.next_action === "board_example") {
              autoTimerRef.current = window.setTimeout(
                () => void start({ action: "next" }),
                Math.max(1600, stream.response.pause_ms || 900),
              );
            }
          },
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to start class stream");
      } finally {
        setLoading(false);
      }
    },
    [examMode, onResponse, sessionId, stop],
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
