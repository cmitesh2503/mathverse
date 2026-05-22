import axios from "axios";

export type TutorMode = "practice" | "learn" | "doubt" | "ocr" | "homework" | "class";
export type ExamMode = "cbse" | "jee";
export type TeachingLanguage = "en-IN" | "hi-IN" | "gu-IN";

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
  text?: string;
  value?: string;
  message?: string;
  x?: number;
  y?: number;
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  radius?: number;
  start_angle?: number;
  end_angle?: number;
  color?: string;
  thickness?: number;
  opacity?: number;
  font_size?: number;
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
    chapter?: string;
    chapter_slug?: string;
    board_problem?: string | null;
    board_steps?: string[];
    whiteboard_context?: WhiteboardState;
    action?: "start" | "next" | "next_concept" | "next_topic" | "continue" | "repeat" | "homework" | "skip_homework" | "finish" | "end" | "end_day" | "help" | "unable" | "not_able" | "solve_pdf_exercises" | "solve_all_exercises" | "solve_all_pdf_exercises" | "next_exercise" | "next_pdf_exercise" | "previous_problem" | "refresh_problem";
    scope?: "all_chapters" | "current_chapter" | "chapter" | string;
    question_index?: number;
    question_data?: HomeworkQuestion;
    answers?: string[];
  };
  context?: {
    exam?: ExamMode;
    student_id?: string;
    grade?: number;
    teaching_language?: TeachingLanguage;
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
  problem_statement?: string | null;
  board_problem?: string | null;
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

export type ConceptMasteryInsights = {
  strong_concepts: string[];
  weak_concepts: string[];
};

export type StudentMarksheetEntry = {
  test_id: string;
  test_name: string;
  test_number: number | null;
  student_id: string;
  student_name: string;
  secured_marks: number;
  max_test_marks: number;
  percentage: number;
  percentage_secured: string;
  evaluated_at?: string;
  answer_sheet_image_url?: string;
  concept_mastery_insights: ConceptMasteryInsights;
};

export type StudentMarksheetResponse = {
  student_id: string;
  total_tests: number;
  marksheet: StudentMarksheetEntry[];
};

export type StepWiseCredits = {
  formula_and_given_data: number;
  step_progression_lines: number;
  final_value_and_units: number;
};

export type DetailedAnswerEntry = {
  question_number: string;
  section: string;
  question_text: string;
  max_marks: number;
  allocated_marks: number;
  step_wise_credits: StepWiseCredits;
  step_by_step_audit: string;
  remediation_advice: string;
};

export type StudentBreakdownResponse = {
  test_id: string;
  test_name: string;
  test_number: number | null;
  student_id: string;
  student_name: string;
  secured_marks: number;
  max_test_marks: number;
  percentage: number;
  percentage_secured: string;
  evaluated_at?: string;
  answer_sheet_image_url?: string;
  concept_mastery_insights: ConceptMasteryInsights;
  detailed_answer_breakdown: DetailedAnswerEntry[];
};

export type BulkUploadPayload = {
  test_id: string;
  test_name: string;
  test_number: number;
  student_id: string;
  student_name: string;
  max_test_marks?: number;
  answer_sheet: File;
};

export type TestMaterialsUploadPayload = {
  test_id: string;
  test_name: string;
  test_number: number;
  question_paper: File;
  marking_scheme: File;
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

export async function getStudentMarksheet(studentId: string): Promise<StudentMarksheetResponse> {
  const { data } = await api.get<StudentMarksheetResponse>(`/api/evaluation/student/${encodeURIComponent(studentId)}/marksheet`);
  return data;
}

export async function getStudentTestBreakdown(studentId: string, testId: string): Promise<StudentBreakdownResponse> {
  const { data } = await api.get<StudentBreakdownResponse>(
    `/api/evaluation/student/${encodeURIComponent(studentId)}/tests/${encodeURIComponent(testId)}/breakdown`,
  );
  return data;
}

export async function uploadAnswerSheet(payload: BulkUploadPayload): Promise<Record<string, unknown>> {
  const formData = new FormData();
  formData.append("test_id", payload.test_id);
  formData.append("test_name", payload.test_name);
  formData.append("test_number", String(payload.test_number));
  formData.append("student_id", payload.student_id);
  formData.append("student_name", payload.student_name);
  if (typeof payload.max_test_marks === "number" && Number.isFinite(payload.max_test_marks)) {
    formData.append("max_test_marks", String(payload.max_test_marks));
  }
  formData.append("answer_sheet", payload.answer_sheet);

  const { data } = await api.post<Record<string, unknown>>("/api/evaluation/bulk-upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function uploadTestMaterials(payload: TestMaterialsUploadPayload): Promise<Record<string, unknown>> {
  const formData = new FormData();
  formData.append("test_id", payload.test_id);
  formData.append("test_name", payload.test_name);
  formData.append("test_number", String(payload.test_number));
  formData.append("question_paper", payload.question_paper);
  formData.append("marking_scheme", payload.marking_scheme);

  const { data } = await api.post<Record<string, unknown>>("/api/evaluation/upload-test-materials", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
