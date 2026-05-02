"use client";

import { create } from "zustand";
import type { ClassResponse, ExamMode, HomeworkQuestion, HomeworkResponse, TutorResponse } from "../services/api";

export type PlanKey = "free" | "cbse_pro" | "jee_lite" | "jee_pro";

export const planLabels: Record<PlanKey, string> = {
  free: "Free",
  cbse_pro: "CBSE Pro",
  jee_lite: "JEE Lite",
  jee_pro: "JEE Pro",
};

export function canUseFeature(plan: PlanKey, feature: "cbse_class" | "voice" | "jee_practice" | "exam" | "analytics" | "speed_mode") {
  if (plan === "jee_pro") return true;
  if (plan === "jee_lite") return feature === "jee_practice" || feature === "exam";
  if (plan === "cbse_pro") return feature === "cbse_class" || feature === "voice" || feature === "analytics";
  return false;
}

type TutorStats = {
  total: number;
  correct: number;
  wrong: number;
  byMistake: Record<string, number>;
  byTopic: Record<string, number>;
  byPattern: Record<string, number>;
  recent: TutorResponse[];
  conceptsLearned: string[];
};

type TutorState = {
  session_id: string;
  exam_mode: ExamMode;
  examMode: ExamMode;
  plan: PlanKey;
  currentTopic: string;
  currentConcept: string | null;
  current_question: string;
  last_response: TutorResponse | null;
  homeworkQuestions: HomeworkQuestion[];
  homeworkAnswers: string[];
  homeworkResult: HomeworkResponse | null;
  pendingClassResponse: ClassResponse | null;
  stats: TutorStats;
  setExamMode: (mode: ExamMode) => void;
  setPlan: (plan: PlanKey) => void;
  setCurrentTopic: (topic: string) => void;
  setCurrentConcept: (concept: string | null) => void;
  setCurrentQuestion: (question: string) => void;
  setHomeworkQuestions: (questions: HomeworkQuestion[]) => void;
  setHomeworkAnswers: (answers: string[]) => void;
  setHomeworkAnswer: (index: number, answer: string) => void;
  setHomeworkResult: (result: HomeworkResponse | null) => void;
  setPendingClassResponse: (response: ClassResponse | null) => void;
  recordTutorSession: (data: { concept?: string | null; mistake_type?: string | null; pattern?: string | null }) => void;
  clearLastResponse: () => void;
  recordResponse: (response: TutorResponse) => void;
};

const initialQuestion = "x^2 - 4 = 0";

export const useTutorStore = create<TutorState>((set) => ({
  session_id: "mathverse-web-session",
  exam_mode: "cbse",
  examMode: "cbse",
  plan: "free",
  currentTopic: "Quadratics",
  currentConcept: null,
  current_question: initialQuestion,
  last_response: null,
  homeworkQuestions: [],
  homeworkAnswers: [],
  homeworkResult: null,
  pendingClassResponse: null,
  stats: {
    total: 0,
    correct: 0,
    wrong: 0,
    byMistake: {},
    byTopic: {},
    byPattern: {},
    recent: [],
    conceptsLearned: [],
  },
  setExamMode: (mode) => set({ exam_mode: mode, examMode: mode }),
  setPlan: (plan) => set({ plan }),
  setCurrentTopic: (topic) => set({ currentTopic: topic }),
  setCurrentConcept: (concept) => set({ currentConcept: concept }),
  setCurrentQuestion: (question) => set({ current_question: question }),
  setHomeworkQuestions: (questions) =>
    set({
      homeworkQuestions: questions,
      homeworkAnswers: questions.map(() => ""),
      homeworkResult: null,
    }),
  setHomeworkAnswers: (answers) => set({ homeworkAnswers: answers }),
  setHomeworkAnswer: (index, answer) =>
    set((state) => {
      const homeworkAnswers = [...state.homeworkAnswers];
      homeworkAnswers[index] = answer;
      return { homeworkAnswers };
    }),
  setHomeworkResult: (result) => set({ homeworkResult: result }),
  setPendingClassResponse: (response) => set({ pendingClassResponse: response }),
  recordTutorSession: ({ concept, mistake_type, pattern }) =>
    set((state) => {
      const byMistake = { ...state.stats.byMistake };
      const byTopic = { ...state.stats.byTopic };
      const byPattern = { ...state.stats.byPattern };
      const conceptsLearned = concept
        ? [concept, ...state.stats.conceptsLearned.filter((item) => item !== concept)].slice(0, 8)
        : state.stats.conceptsLearned;

      if (mistake_type) {
        byMistake[mistake_type] = (byMistake[mistake_type] || 0) + 1;
      }

      if (pattern) {
        byPattern[pattern] = (byPattern[pattern] || 0) + 1;
      }

      if (mistake_type) {
        byTopic[state.currentTopic] = (byTopic[state.currentTopic] || 0) + 1;
      }

      return {
        stats: {
          ...state.stats,
          byMistake,
          byTopic,
          byPattern,
          conceptsLearned,
        },
      };
    }),
  clearLastResponse: () => set({ last_response: null }),
  recordResponse: (response) =>
    set((state) => {
      const total = state.stats.total + 1;
      const correct = state.stats.correct + (response.correct ? 1 : 0);
      const wrong = state.stats.wrong + (response.correct === false ? 1 : 0);
      const byMistake = { ...state.stats.byMistake };
      const byTopic = { ...state.stats.byTopic };
      const byPattern = { ...state.stats.byPattern };

      if (response.mistake_type) {
        byMistake[response.mistake_type] = (byMistake[response.mistake_type] || 0) + 1;
      }

      if (response.correct === false) {
        byTopic[state.currentTopic] = (byTopic[state.currentTopic] || 0) + 1;
        const pattern = inferPattern(state.current_question);
        if (pattern) {
          byPattern[pattern] = (byPattern[pattern] || 0) + 1;
        }
      }

      return {
        last_response: response,
        current_question: extractPrompt(response.next_question) || state.current_question,
        stats: {
          total,
          correct,
          wrong,
          byMistake,
          byTopic,
          byPattern,
          recent: [response, ...state.stats.recent].slice(0, 8),
          conceptsLearned: state.stats.conceptsLearned,
        },
      };
    }),
}));

function extractPrompt(nextQuestion?: string | null): string | null {
  if (!nextQuestion) return null;
  const parts = nextQuestion.split("\n").map((part) => part.trim()).filter(Boolean);
  return parts[parts.length - 1] || null;
}

function inferPattern(question: string): string | null {
  const normalized = question.replace(/\s+/g, "").toLowerCase();
  if (/x\^?2-\d+=0/.test(normalized) || normalized.includes("x**2-")) return "Difference of Squares";
  if (/x\^?2[+-]\d+x[+-]\d+/.test(normalized) || normalized.includes("x**2")) return "Factorization";
  if (normalized.includes("discriminant") || normalized.includes("formula")) return "Quadratic Formula";
  return null;
}
