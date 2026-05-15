type VoiceOptions = {
  chunks?: string[];
  rate?: number;
  pauseMs?: number;
  onStart?: () => void;
  onChunkStart?: (index: number, chunk: string) => void;
  onEnd?: () => void;
};

export type VoiceController = {
  pause: () => void;
  resume: () => void;
  stop: () => void;
};

function splitText(text: string) {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

function sanitizeSpokenChunk(chunk: string) {
  return chunk
    .replace(/\[(pause|break)\]/gi, " ")
    .replace(/\((pause|break)\)/gi, " ")
    .replace(/\bpause\s+(here|now|for a moment)\b[,:;.-]*/gi, " ")
    .replace(/^\s*pause\s*[,:;.-]*/i, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function playVoiceStream(text: string, options: VoiceOptions = {}): VoiceController {
  const chunks = (options.chunks?.length ? options.chunks : splitText(text))
    .map((chunk) => sanitizeSpokenChunk(chunk))
    .filter(Boolean);
  const rate = typeof options.rate === "number" ? Math.min(1.2, Math.max(0.65, options.rate)) : 0.8;
  const pauseMs = typeof options.pauseMs === "number" ? Math.max(120, options.pauseMs) : 420;
  let stopped = false;
  let index = 0;

  options.onStart?.();

  if (typeof window === "undefined" || !("speechSynthesis" in window) || chunks.length === 0) {
    chunks.forEach((chunk, chunkIndex) => options.onChunkStart?.(chunkIndex, chunk));
    options.onEnd?.();
    return { pause: () => undefined, resume: () => undefined, stop: () => undefined };
  }

  window.speechSynthesis.cancel();

  const speakNext = () => {
    if (stopped) return;
    if (index >= chunks.length) {
      options.onEnd?.();
      return;
    }

    const chunkIndex = index;
    const utterance = new SpeechSynthesisUtterance(chunks[chunkIndex]);
    utterance.rate = rate;
    utterance.pitch = 1;
    utterance.onstart = () => options.onChunkStart?.(chunkIndex, chunks[chunkIndex]);
    utterance.onend = () => {
      index += 1;
      window.setTimeout(speakNext, pauseMs);
    };
    utterance.onerror = () => {
      index += 1;
      speakNext();
    };

    window.speechSynthesis.speak(utterance);
  };

  speakNext();

  return {
    pause: () => window.speechSynthesis.pause(),
    resume: () => window.speechSynthesis.resume(),
    stop: () => {
      stopped = true;
      window.speechSynthesis.cancel();
    },
  };
}
