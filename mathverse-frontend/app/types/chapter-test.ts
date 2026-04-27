export type ChapterTestQuestionKind = "numeric" | "pair" | "short";

export type ChapterTestQuestion = {
  id: string;
  prompt: string;
  concept_title?: string;
  kind: ChapterTestQuestionKind;
  answer_format: string;
};

export type ChapterTest = {
  test_id: string;
  title: string;
  chapter_label: string;
  topic_title: string;
  instructions: string;
  generated_at: string;
  questions: ChapterTestQuestion[];
};

export type ChapterTestFeedback = {
  question_id: string;
  prompt: string;
  correct: boolean;
  score: number;
  max_score: number;
  submitted: string;
  expected: string;
  feedback: string;
};

export type ChapterTestResult = {
  test_id: string;
  score: number;
  max_score: number;
  percentage: number;
  verdict: string;
  submitted_at: string;
  feedback: ChapterTestFeedback[];
};
