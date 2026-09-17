import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { playVoiceStream, type VoiceController } from "../../services/voice";
import type { TeachingLanguage } from "../../services/api";
import type { LessonEvent, LessonTimeline as LessonTimelineModel } from "../../services/lessonTimeline";

type VisualLessonEvent =
  | Extract<LessonEvent, { type: "write" }>
  | Extract<LessonEvent, { type: "draw" }>
  | Extract<LessonEvent, { type: "plot" }>;

export type RenderedBoardEvent = {
  key: string;
  order: number;
  event: VisualLessonEvent;
};

type Args = {
  timeline: LessonTimelineModel;
  autoPlay: boolean;
  teachingLanguage: TeachingLanguage;
  onComplete?: () => void;
};

function isVisualEvent(event: LessonEvent): event is VisualLessonEvent {
  return event.type === "write" || event.type === "draw" || event.type === "plot";
}

function visualKey(event: VisualLessonEvent, index: number) {
  return `${event.type}-${event.id || index}`;
}

function eventDuration(event: LessonEvent) {
  if (event.type === "pause") return Math.max(250, event.durationMs);
  if (event.type === "highlight") return event.durationMs ?? 650;
  return event.durationMs ?? 520;
}

export function useLessonTimeline({ timeline, autoPlay, teachingLanguage, onComplete }: Args) {
  const [cursor, setCursor] = useState(0);
  const [boardEvents, setBoardEvents] = useState<RenderedBoardEvent[]>([]);
  const [currentSpeech, setCurrentSpeech] = useState("");
  const [highlightedTargetId, setHighlightedTargetId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [isPaused, setIsPaused] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [completed, setCompleted] = useState(false);
  const appliedIndexRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const voiceRef = useRef<VoiceController | null>(null);
  const completionReportedRef = useRef(false);
  const timelineIdRef = useRef(timeline.id);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopVoice = useCallback(() => {
    voiceRef.current?.stop();
    voiceRef.current = null;
    setIsSpeaking(false);
  }, []);

  const reset = useCallback(
    (playAfterReset: boolean) => {
      clearTimer();
      stopVoice();
      appliedIndexRef.current = null;
      completionReportedRef.current = false;
      setCursor(0);
      setBoardEvents([]);
      setCurrentSpeech("");
      setHighlightedTargetId(null);
      setCompleted(false);
      setIsPaused(false);
      setIsPlaying(playAfterReset);
    },
    [clearTimer, stopVoice],
  );

  useEffect(() => {
    timelineIdRef.current = timeline.id;

    const resetTimer = window.setTimeout(() => {
      reset(autoPlay);
    }, 0);

    return () => window.clearTimeout(resetTimer);
  }, [autoPlay, reset, timeline.events, timeline.id]);

  useEffect(() => {
    if (!isPlaying || isPaused || completed) return;

    const event = timeline.events[cursor];
    const currentTimelineId = timeline.id;

    clearTimer();
    timerRef.current = window.setTimeout(() => {
      if (timelineIdRef.current !== currentTimelineId) return;

      if (!event) {
        setIsPlaying(false);
        setIsSpeaking(false);
        setCompleted(true);
        setHighlightedTargetId(null);
        if (!completionReportedRef.current) {
          completionReportedRef.current = true;
          onCompleteRef.current?.();
        }
        return;
      }

      if (appliedIndexRef.current !== cursor) {
        appliedIndexRef.current = cursor;

        if (isVisualEvent(event)) {
          setBoardEvents((current) => {
            const key = visualKey(event, cursor);
            if (current.some((item) => item.key === key)) return current;
            return [...current, { key, order: cursor, event }];
          });
        }

        if (event.type === "highlight") {
          setHighlightedTargetId(event.targetId);
        }

        if (event.type === "speak") {
          setCurrentSpeech(event.text);
          voiceRef.current = playVoiceStream(event.text, {
            chunks: [event.text],
            lang: teachingLanguage,
            rate: 0.9,
            pauseMs: 180,
            onStart: () => {
              if (timelineIdRef.current === currentTimelineId) {
                setIsSpeaking(true);
              }
            },
            onEnd: () => {
              if (timelineIdRef.current !== currentTimelineId) return;
              setIsSpeaking(false);
              setCursor((current) => (current === cursor ? current + 1 : current));
            },
          });
          return;
        }
      }

      if (event.type === "speak") {
        return;
      }

      timerRef.current = window.setTimeout(() => {
        setCursor((current) => (current === cursor ? current + 1 : current));
      }, eventDuration(event));
    }, 0);

    return clearTimer;
  }, [clearTimer, completed, cursor, isPaused, isPlaying, teachingLanguage, timeline.events, timeline.id]);

  useEffect(() => {
    return () => {
      clearTimer();
      voiceRef.current?.stop();
    };
  }, [clearTimer]);

  const play = useCallback(() => {
    if (completed) {
      reset(true);
      return;
    }

    setIsPlaying(true);
    setIsPaused(false);
    const currentEvent = timeline.events[cursor];
    if (currentEvent?.type === "speak" && appliedIndexRef.current === cursor) {
      voiceRef.current?.resume();
      setIsSpeaking(true);
    }
  }, [completed, cursor, reset, timeline.events]);

  const pause = useCallback(() => {
    clearTimer();
    voiceRef.current?.pause();
    setIsPaused(true);
    setIsSpeaking(false);
  }, [clearTimer]);

  const togglePlay = useCallback(() => {
    if (!isPlaying || isPaused) {
      play();
      return;
    }
    pause();
  }, [isPaused, isPlaying, pause, play]);

  const replay = useCallback(() => {
    reset(true);
  }, [reset]);

  const progress = useMemo(() => {
    if (!timeline.events.length) return 100;
    if (completed) return 100;
    return Math.min(100, Math.round((cursor / timeline.events.length) * 100));
  }, [completed, cursor, timeline.events.length]);

  const currentEvent = timeline.events[cursor] ?? null;

  return {
    boardEvents,
    currentEvent,
    currentEventIndex: currentEvent ? cursor : null,
    currentSpeech,
    highlightedTargetId,
    isPlaying,
    isPaused,
    isSpeaking,
    completed,
    progress,
    play,
    pause,
    togglePlay,
    replay,
  };
}
