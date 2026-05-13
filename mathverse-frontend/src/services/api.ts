import axios from "axios";

export type TutorMode = "practice" | "learn" | "doubt" | "ocr" | "homework" | "class";
export type ExamMode = "cbse" | "jee";

export type WhiteboardState = {
  mode?: "concept" | "worked_example" | "student_try" | string;
  title?: string;
  subtitle?: string;
  chalk_lines?: string[];
  equations?: string[];
  problem?: string;
  solution_steps?: string[];
  answer?: string;
  actions?: WhiteboardAction[];
};

export type WhiteboardAction = {
  action: string;
  content?: string;
  label?: string;
  expression?: string;
  reason?: string;
  warnings?: number;
  score?: number;
  correct?: number;
  wrong?: number;
  points?: Array<[number, number]>;
  metadata?: Record<string, unknown>;
};

export type TutorPayload = {
  session_id: string;
  mode: TutorMode;
  input: {
    question?: string;
    answer?: string;
    topic?: string;
    action?: "start" | "next" | "next_concept" | "next_topic" | "continue" | "repeat" | "homework" | "skip_homework" | "finish" | "end" | "end_day" | "help" | "unable" | "not_able" | "solve_pdf_exercises" | "solve_all_exercises" | "solve_all_pdf_exercises" | "next_exercise" | "next_pdf_exercise";
    scope?: "all_chapters" | "current_chapter" | "chapter" | string;
    question_index?: number;
    question_data?: HomeworkQuestion;
    answers?: string[];
  };
  context?: {
    exam?: ExamMode;
    student_id?: string;
    grade?: number;
  };
};

export type TutorResponse = {
  correct: boolean | null;
  mistake_type?: string | null;
  hint?: string | null;
  explanation?: string | string[] | null;
  steps?: string[];
  shortcut?: string | null;
  speed_hint?: string | null;
  adaptive_hint?: string | null;
  next_question?: string | null;
};

export type LearnResponse = {
  concept?: string | null;
  topic?: string | null;
  chapter?: string | null;
  explanation?: string | null;
  example?: string | null;
  check_question?: string | null;
  next_action?: "practice" | "next_concept" | string;
  shortcut?: string | null;
  speed_hint?: string | null;
  steps?: string[];
};

export type HomeworkQuestion = {
  prompt?: string;
  question?: string;
  answer?: string | number | Array<string | number>;
  topic?: string;
};

export type HomeworkResponse = {
  score: number | null;
  weak_areas: string[];
  explanation: string;
  questions?: HomeworkQuestion[];
  next_class?: ClassResponse;
  next_topic?: string | null;
  next_concept?: string | null;
  help_solutions?: Array<{
    index: number;
    question?: string;
    steps?: string[];
    answer?: string;
  }>;
  next_recommendation: string;
};

export type HomeworkHelpResponse = {
  type: "homework_help";
  explanation: string;
  question?: HomeworkQuestion;
  steps: string[];
  whiteboard?: WhiteboardState;
  voice_text?: string;
};

export type ClassResponse = {
  type: "teach" | "board_example" | "question" | "evaluation" | "homework" | "chapter_complete" | "exercise_solution";
  chapter?: string | null;
  chapter_label?: string | null;
  topic?: string | null;
  concept?: string | null;
  explanation: string;
  steps: string[];
  question?: string | null;
  correct?: boolean | null;
  mistake_type?: string | null;
  hint?: string | null;
  next_action?: string | null;
  example?: string | null;
  voice_text: string;
  pattern?: string | null;
  shortcut?: string | null;
  speed_hint?: string | null;
  whiteboard?: WhiteboardState;
  whiteboard_actions?: WhiteboardAction[];
  homework?: HomeworkQuestion[] | null;
  session_notes?: string[];
  note_cards?: string[];
  pace?: "slow" | "normal" | string;
  pause_ms?: number;
  session_time_left_seconds?: number | null;
  session_duration_seconds?: number | null;
  session_expired?: boolean;
  avatar_voice?: {
    style?: string;
    pace?: string;
    sync_to_whiteboard?: boolean;
    pause_ms?: number;
  };
  avatar_stream?: {
    voice_chunks: string[];
    steps: string[];
    pace?: string;
    pause_ms?: number;
  };
  content?: {
    chapter?: string | null;
    chapter_label?: string | null;
    concept?: string | null;
    explanation: string;
    steps: string[];
    example?: string | null;
    voice_text: string;
    question?: string | null;
    pattern?: string | null;
    recognition_tip?: string | null;
    shortcut?: string | null;
    speed_hint?: string | null;
    whiteboard?: WhiteboardState;
    whiteboard_actions?: WhiteboardAction[];
    homework?: HomeworkQuestion[] | null;
    session_notes?: string[];
    note_cards?: string[];
    avatar_voice?: {
      style?: string;
      pace?: string;
      sync_to_whiteboard?: boolean;
      pause_ms?: number;
    };
    avatar_stream?: {
      voice_chunks: string[];
      steps: string[];
      pace?: string;
      pause_ms?: number;
    };
    questions?: HomeworkQuestion[];
  };
};

export type AttemptRecord = {
  session_id?: string;
  student_id?: string;
  grade?: number;
  exam?: ExamMode;
  mode?: string;
  chapter?: string | null;
  topic?: string | null;
  concept?: string | null;
  question?: string | null;
  answer?: string | null;
  correct?: boolean | null;
  mistake_type?: string | null;
  difficulty?: string;
  pattern?: string | null;
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function shouldRetryRequest(error: unknown) {
  if (!axios.isAxiosError(error)) return false;
  if (error.response) return false;
  const code = error.code || "";
  return code === "ECONNABORTED" || code === "ERR_NETWORK" || code === "ETIMEDOUT";
}

export async function sendAnswer<T = TutorResponse>(payload: TutorPayload): Promise<T> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const { data } = await api.post<T>("/api/tutor/ask", payload);
      return data;
    } catch (error) {
      if (attempt === 0 && shouldRetryRequest(error)) {
        await sleep(700);
        continue;
      }
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail || error.response?.data?.error;
        throw new Error(detail || `Could not reach MathVerse API at ${API_BASE_URL}`);
      }
      throw error;
    }
  }
  throw new Error(`Could not reach MathVerse API at ${API_BASE_URL}`);
}

export async function getAttemptHistory(studentId: string): Promise<AttemptRecord[]> {
  const { data } = await api.get<{ attempts: AttemptRecord[] }>(`/api/tutor/attempts/${encodeURIComponent(studentId)}`);
  return data.attempts || [];
}
