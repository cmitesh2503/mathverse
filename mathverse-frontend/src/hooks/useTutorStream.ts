"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ClassResponse, ExamMode, TutorPayload } from "../services/api";
import { startClassStream, type TutorStreamData } from "../services/tutorStream";
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
  const lastGradeRef = useRef<number | undefined>(undefined);
  const lastSubjectRef = useRef<string | undefined>(undefined);
  const prefetchedStreamRef = useRef<TutorStreamData | null>(null);
  const prefetchInFlightRef = useRef<Promise<void> | null>(null);
  const silentRetryRef = useRef(0);

  const stop = useCallback(() => {
    voiceRef.current?.stop();
    if (autoTimerRef.current) window.clearTimeout(autoTimerRef.current);
  }, []);

  const prefetchNextContinue = useCallback((grade?: number, subject?: string) => {
    if (prefetchedStreamRef.current || prefetchInFlightRef.current) {
      return;
    }
    const requestedGrade = typeof grade === "number" ? grade : undefined;
    prefetchInFlightRef.current = (async () => {
      try {
        const stream = await startClassStream({
          session_id: sessionId,
          input: {
            action: "continue",
            grade: requestedGrade,
            subject: subject || "math",
          },
          context: {
            exam: requestedGrade ? "jee" : examMode,
            grade: requestedGrade,
          },
        });
        prefetchedStreamRef.current = stream;
      } catch {
        // Silent prefetch failure: main flow can still request on-demand.
      } finally {
        prefetchInFlightRef.current = null;
      }
    })();
  }, [examMode, sessionId]);

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
      input: TutorPayload["input"] & { grade?: number; subject?: string } = { action: "start", grade: 11, subject: "math" },
      options?: { silent?: boolean },
    ) => {
      stop();
      if (!options?.silent) {
        setLoading(true);
      }
      setError(null);
      setPaused(false);
      lastGradeRef.current = typeof input.grade === "number" ? input.grade : lastGradeRef.current;
      lastSubjectRef.current = typeof input.subject === "string" ? input.subject : lastSubjectRef.current;
      const isAutoContinueTurn = options?.silent && String(input.action || "").toLowerCase() === "continue";
      if (!isAutoContinueTurn) {
        prefetchedStreamRef.current = null;
      }

      try {
        const requestedGrade = typeof input.grade === "number" ? input.grade : undefined;
        //const requestedExamMode = requestedGrade ? "jee" : examMode;
        const stream =
          isAutoContinueTurn && prefetchedStreamRef.current
            ? prefetchedStreamRef.current
            : await startClassStream({
                session_id: sessionId,
                input,
                context: {
                  exam:  examMode,
                  grade: requestedGrade,
                },
              });
        if (isAutoContinueTurn) {
          prefetchedStreamRef.current = null;
        }
        silentRetryRef.current = 0;

        setResponse(stream.response);
        onResponse?.(stream.response);

        voiceRef.current = playVoiceStream(stream.voice_chunks.join(". "), {
          chunks: stream.voice_chunks,
          onStart: () => setIsSpeaking(true),
          onChunkStart: () => undefined,
          onEnd: () => {
            setVisibleSteps(stream.steps);
            setIsSpeaking(false);
            const autoAdvanceEligible =
              stream.response.type === "teach" &&
              stream.response.next_action !== "question" &&
              stream.response.next_action !== "homework" &&
              stream.response.next_action !== "finish";

            if (autoAdvanceEligible) {
              prefetchNextContinue(lastGradeRef.current, lastSubjectRef.current);
              autoTimerRef.current = window.setTimeout(
                () =>
                  void start({
                    action: "continue",
                    grade: lastGradeRef.current,
                    subject: lastSubjectRef.current || "math",
                  }, { silent: true }),
                Math.max(1800, stream.response.pause_ms || 1500),
              );
            }
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
    [examMode, onResponse, prefetchNextContinue, sessionId, stop],
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
