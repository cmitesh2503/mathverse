import { sendAnswer, type ClassResponse, type ExamMode } from "./api";

type StartClassPayload = {
  session_id: string;
  mode?: "class";
  input?: {
    grade?: number;
    subject?: string;
    action?: "start" | "next" | "repeat" | "homework" | "skip_homework" | "finish" | "end" | "end_day";
    answer?: string;
  };
  context?: {
    exam?: ExamMode;
    student_id?: string;
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
  const voiceText = response.voice_text || response.content?.voice_text || response.explanation || response.content?.explanation || "";
  const whiteboard = response.whiteboard || response.content?.whiteboard;
  const steps =
    response.steps?.length
      ? response.steps
      : response.content?.steps?.length
        ? response.content.steps
        : whiteboard?.solution_steps?.length
          ? whiteboard.solution_steps
          : [...(whiteboard?.equations || []), ...(whiteboard?.chalk_lines || [])];

  return {
    response,
    voice_chunks: avatarStream?.voice_chunks?.length ? avatarStream.voice_chunks : splitText(voiceText),
    steps: avatarStream?.steps?.length ? avatarStream.steps : steps,
  };
}

export async function startClassStream(payload: StartClassPayload): Promise<TutorStreamData> {
  const response = await sendAnswer<ClassResponse>({
    session_id: payload.session_id,
    mode: "class",
    input: payload.input || { grade: 9, subject: "math" },
    context: payload.context,
  });

  return formatForAvatar(response);
}
