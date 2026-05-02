type VoiceOptions = {
  chunks?: string[];
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

export function playVoiceStream(text: string, options: VoiceOptions = {}): VoiceController {
  const chunks = (options.chunks?.length ? options.chunks : splitText(text)).filter(Boolean);
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
    utterance.rate = 0.92;
    utterance.pitch = 1;
    utterance.onstart = () => options.onChunkStart?.(chunkIndex, chunks[chunkIndex]);
    utterance.onend = () => {
      index += 1;
      window.setTimeout(speakNext, 120);
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
