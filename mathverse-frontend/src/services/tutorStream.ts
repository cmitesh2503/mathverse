import { sendAnswer, type ClassResponse, type ExamMode, type TutorPayload } from "./api";

type StartClassPayload = {
  session_id: string;
  mode?: "class";
  input?: TutorPayload["input"] & { grade?: number; subject?: string };
  context?: {
    exam?: ExamMode;
    student_id?: string;
    grade?: number;
  };
};

export type TutorStreamData = {
  response: ClassResponse;
  voice_chunks: string[];
  steps: string[];
};

function splitText(text: string) {
  const chunks: string[] = [];
  text
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .forEach((sentence) => {
      const words = sentence.split(/\s+/);
      for (let index = 0; index < words.length; index += 18) {
        chunks.push(words.slice(index, index + 18).join(" "));
      }
    });
  return chunks;
}

function formatForAvatar(response: ClassResponse): TutorStreamData {
  const avatarStream = response.avatar_stream || response.content?.avatar_stream;
  const whiteboard = response.whiteboard || response.content?.whiteboard;
  const steps =
    response.steps?.length
      ? response.steps
      : response.content?.steps?.length
        ? response.content.steps
        : whiteboard?.solution_steps?.length
          ? whiteboard.solution_steps
          : [...(whiteboard?.equations || []), ...(whiteboard?.chalk_lines || [])];
  const voiceText =
    response.voice_text ||
    response.content?.voice_text ||
    response.explanation ||
    response.content?.explanation ||
    (steps.length ? steps.slice(0, 4).join(". ") : "") ||
    "Let's continue this concept step by step.";

  return {
    response,
    voice_chunks: avatarStream?.voice_chunks?.length ? avatarStream.voice_chunks : splitText(voiceText),
    steps: avatarStream?.steps?.length ? avatarStream.steps : steps,
  };
}

export async function startClassStream(payload: StartClassPayload): Promise<TutorStreamData> {
  const response = await sendAnswer<ClassResponse | { error?: string; detail?: string }>({
    session_id: payload.session_id,
    mode: "class",
    input: payload.input || { action: "start", grade: 10, subject: "math" },
    context: payload.context,
  });

  if ("error" in response && response.error) {
    throw new Error(response.error);
  }

  if ("detail" in response && response.detail) {
    throw new Error(response.detail);
  }

  return formatForAvatar(response as ClassResponse);
}
