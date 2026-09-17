"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type { PageKey } from "../App";
import { ChapterOverview } from "../components/classroom/ChapterOverview";
import { ClassroomControls } from "../components/classroom/ClassroomControls";
import { ClassroomLayout } from "../components/classroom/ClassroomLayout";
import { ConceptNavigator } from "../components/classroom/ConceptNavigator";
import { useLessonTimeline } from "../components/classroom/LessonTimeline";
import { SynchronizedWhiteboard } from "../components/classroom/SynchronizedWhiteboard";
import { TutorPanel, type ClassroomDiscussionTurn } from "../components/classroom/TutorPanel";
import { UpgradeNotice } from "../components/UpgradeNotice";
import { getKnowledgeFactoryCurriculum, type ClassResponse, type TeachingLanguage } from "../services/api";
import {
  CLASSROOM_GRADES,
  chapterLessonFromKnowledgeFactory,
  TEACHING_LANGUAGES,
  type ChapterLesson,
  type ClassroomGrade,
  type LessonConcept,
  type LessonEvent,
  type LessonTimeline,
  type StudentLevel,
} from "../services/lessonTimeline";
import { canUseFeature, useTutorStore } from "../store/useTutorStore";

type Props = {
  onNavigate: (page: PageKey) => void;
};

type ChapterSlug = string;

const STUDENT_LEVELS: Array<{ value: StudentLevel; label: string; description: string }> = [
  {
    value: "standard",
    label: "Standard",
    description: "Balanced pace with clear examples.",
  },
  {
    value: "foundation",
    label: "Foundation",
    description: "Slower steps and more intuition.",
  },
  {
    value: "advanced",
    label: "Advanced",
    description: "Adds patterns after the concept is clear.",
  },
];

function normalizeText(value?: string | null) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function chapterSlugFromResponse(
  response: ClassResponse | null,
  chapters: Array<{ slug: string; title: string }>,
): ChapterSlug | null {
  const chapterText = response?.chapter || response?.content?.chapter || response?.topic || null;
  if (!chapterText) return null;

  const normalizedChapter = normalizeText(chapterText);
  const match = chapters.find((chapter) => {
    return (
      chapter.slug === chapterText ||
      normalizeText(chapter.slug) === normalizedChapter ||
      normalizeText(chapter.title) === normalizedChapter
    );
  });

  return match?.slug ?? null;
}

function conceptIndexFromResponse(chapter: ChapterLesson, response: ClassResponse | null) {
  const conceptText = response?.concept || response?.content?.concept || response?.topic || null;
  if (!conceptText) return 0;

  const normalizedConcept = normalizeText(conceptText);
  const conceptIndex = chapter.concepts.findIndex((concept) => {
    const candidates = [concept.id, concept.title, concept.shortTitle, concept.summary];
    return candidates.some((candidate) => {
      const normalizedCandidate = normalizeText(candidate);
      return normalizedCandidate === normalizedConcept || normalizedCandidate.includes(normalizedConcept);
    });
  });

  return Math.max(0, conceptIndex);
}

function eventStepLabel(event: LessonEvent | null, eventIndex: number | null, totalEvents: number) {
  if (!event) return "Lesson complete";

  const prefix = eventIndex === null ? "Step" : `Step ${eventIndex + 1} of ${totalEvents}`;

  if (event.type === "speak") return `${prefix}: tutor explanation`;
  if (event.type === "write") return `${prefix}: writing on the board`;
  if (event.type === "draw") return `${prefix}: drawing the diagram`;
  if (event.type === "plot") return `${prefix}: plotting the graph`;
  if (event.type === "highlight") return `${prefix}: highlighting the key idea`;
  return `${prefix}: short thinking pause`;
}

function chapterProgressFor(
  chapter: ChapterLesson,
  currentConcept: LessonConcept,
  completedConceptIds: string[],
  currentConceptProgress: number,
) {
  const completedIds = new Set(completedConceptIds);
  const completedCount = chapter.concepts.filter((concept) => completedIds.has(concept.id)).length;
  const currentContribution = completedIds.has(currentConcept.id) ? 0 : currentConceptProgress / 100;

  return clampPercent(((completedCount + currentContribution) / Math.max(1, chapter.concepts.length)) * 100);
}

function buildQuestionTimeline(chapter: ChapterLesson, concept: LessonConcept, question: string): LessonTimeline {
  const confusionDetected = /\b(confused|stuck|lost|again|repeat|slow|why|not understand|did not understand|don't understand|doubt)\b/i.test(question);
  const spokenAnswer = confusionDetected
    ? `Good catch. Let us make ${concept.shortTitle} smaller. ${concept.intuition}`
    : `Good question. Keep this idea in mind: ${concept.summary}`;

  return {
    id: `${chapter.slug}-${concept.id}-question-${Date.now()}`,
    chapterTitle: chapter.title,
    conceptTitle: concept.title,
    events: [
      { type: "speak", text: spokenAnswer },
      { type: "write", id: "question-key-idea", kind: "note", content: concept.summary },
      { type: "write", id: "question-prompt", kind: "question", content: question },
      { type: "speak", text: "Now connect your question to the key idea on the board." },
      { type: "pause", durationMs: 500 },
    ],
  };
}

export default function Classroom({ onNavigate }: Props) {
  const examMode = useTutorStore((state) => state.exam_mode);
  const plan = useTutorStore((state) => state.plan);
  const pendingClassResponse = useTutorStore((state) => state.pendingClassResponse);
  const setCurrentTopic = useTutorStore((state) => state.setCurrentTopic);
  const setCurrentConcept = useTutorStore((state) => state.setCurrentConcept);
  const setCurrentQuestion = useTutorStore((state) => state.setCurrentQuestion);
  const setPendingClassResponse = useTutorStore((state) => state.setPendingClassResponse);
  const recordTutorSession = useTutorStore((state) => state.recordTutorSession);

  const [selectedGrade, setSelectedGrade] = useState<ClassroomGrade>(10);
  const [teachingLanguage, setTeachingLanguage] = useState<TeachingLanguage>("en-IN");
  const [selectedChapterSlug, setSelectedChapterSlug] = useState<ChapterSlug>("");
  const [curriculum, setCurriculum] = useState<Awaited<ReturnType<typeof getKnowledgeFactoryCurriculum>> | null>(null);
  const [curriculumError, setCurriculumError] = useState<string | null>(null);
  const [curriculumLoading, setCurriculumLoading] = useState(true);
  const [studentLevel, setStudentLevel] = useState<StudentLevel>("standard");
  const [classStarted, setClassStarted] = useState(false);
  const [conceptIndex, setConceptIndex] = useState(0);
  const [completedConceptIds, setCompletedConceptIds] = useState<string[]>([]);
  const [questionText, setQuestionText] = useState("");
  const [discussionTurns, setDiscussionTurns] = useState<ClassroomDiscussionTurn[]>([]);
  const [questionTimeline, setQuestionTimeline] = useState<LessonTimeline | null>(null);
  const [confusionDetected, setConfusionDetected] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [handoffNotice, setHandoffNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setCurriculumLoading(true);
    setCurriculumError(null);
    void getKnowledgeFactoryCurriculum(selectedGrade)
      .then((data) => {
        if (cancelled) return;
        console.info("[CLASSROOM] curriculum source = Knowledge Factory API");
        setCurriculum(data);
        setSelectedChapterSlug((current) => current || data.chapters[0]?.slug || "");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setCurriculumError(error instanceof Error ? error.message : "Knowledge Factory curriculum could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setCurriculumLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedGrade]);

  const selectedChapter = curriculum?.chapters.find((chapter) => chapter.slug === selectedChapterSlug) ?? curriculum?.chapters[0];
  const selectedChapterIndex = Math.max(
    0,
    curriculum?.chapters.findIndex((chapter) => chapter.slug === selectedChapter?.slug) ?? 0,
  );
  const selectedChapterIsFree = examMode === "cbse" && selectedChapterIndex === 0;
  const hasFullClassAccess = examMode === "cbse" ? canUseFeature(plan, "cbse_class") : canUseFeature(plan, "jee_practice");
  const classAllowed = hasFullClassAccess || selectedChapterIsFree;
  const gradeOptions: ClassroomGrade[] = examMode === "cbse" ? [10] : [...CLASSROOM_GRADES];
  const tutorLabel = examMode === "cbse" ? "CBSE Tutor" : "JEE Tutor";

  const chapter = useMemo(() => {
    if (!selectedChapter) return null;
    return chapterLessonFromKnowledgeFactory(selectedChapter, selectedGrade, curriculum?.knowledge_package);
  }, [curriculum?.knowledge_package, selectedChapter, selectedGrade]);

  const runtimeChapter = chapter ?? chapterLessonFromKnowledgeFactory(
    { id: "loading", slug: "loading", title: "Loading", concepts: [] },
    selectedGrade,
    curriculum?.knowledge_package,
  );
  const currentConcept = runtimeChapter.concepts[conceptIndex] ?? runtimeChapter.concepts[0];
  const conceptTimeline = useMemo(
    () => ({
      id: `${runtimeChapter.slug}-${currentConcept.id}-concept`,
      chapterTitle: runtimeChapter.title,
      conceptTitle: currentConcept.title,
      events: currentConcept.events,
    }),
    [currentConcept, runtimeChapter.slug, runtimeChapter.title],
  );
  const activeTimeline = questionTimeline ?? conceptTimeline;
  const activeTimelineKind = questionTimeline ? "question" : "concept";

  const resetRuntimeForNewSelection = useCallback(() => {
    setQuestionTimeline(null);
    setConfusionDetected(false);
  }, []);

  const handleTimelineComplete = useCallback(() => {
    if (activeTimelineKind !== "concept") return;

    setCompletedConceptIds((current) => {
      if (current.includes(currentConcept.id)) return current;
      return [...current, currentConcept.id];
    });
    recordTutorSession({
      concept: currentConcept.title,
      pattern: examMode === "jee" ? currentConcept.shortTitle : null,
    });
  }, [activeTimelineKind, currentConcept.id, currentConcept.shortTitle, currentConcept.title, examMode, recordTutorSession]);

  const timelineRuntime = useLessonTimeline({
    timeline: activeTimeline,
    autoPlay: classStarted,
    teachingLanguage,
    onComplete: handleTimelineComplete,
  });

  const chapterProgress = chapter && currentConcept ? chapterProgressFor(
    runtimeChapter,
    currentConcept,
    completedConceptIds,
    activeTimelineKind === "concept" ? timelineRuntime.progress : 0,
  ) : 0;
  const currentStepLabel = eventStepLabel(
    timelineRuntime.currentEvent,
    timelineRuntime.currentEventIndex,
    activeTimeline.events.length,
  );

  useEffect(() => {
    if (!chapter || !currentConcept) return;
    setCurrentTopic(runtimeChapter.title);
    setCurrentConcept(currentConcept.title);
    setCurrentQuestion(currentConcept.checkQuestion);
  }, [chapter, currentConcept, runtimeChapter, setCurrentConcept, setCurrentQuestion, setCurrentTopic]);

  useEffect(() => {
    if (!pendingClassResponse) return;

    const targetSlug = chapterSlugFromResponse(pendingClassResponse, curriculum?.chapters ?? []) ?? selectedChapterSlug;
    const targetChapterData = curriculum?.chapters.find((item) => item.slug === targetSlug);
    if (!targetChapterData) return;
    const targetChapter = chapterLessonFromKnowledgeFactory(
      targetChapterData,
      selectedGrade,
      curriculum?.knowledge_package,
    );
    const nextConceptIndex = conceptIndexFromResponse(targetChapter, pendingClassResponse);
    const responseConcept = pendingClassResponse.concept || pendingClassResponse.content?.concept || targetChapter.concepts[nextConceptIndex]?.title;
    const responseTopic = pendingClassResponse.topic || pendingClassResponse.chapter || pendingClassResponse.content?.chapter || targetChapter.title;

    setSelectedChapterSlug(targetSlug);
    setConceptIndex(nextConceptIndex);
    setCompletedConceptIds(targetChapter.concepts.slice(0, nextConceptIndex).map((concept) => concept.id));
    setQuestionTimeline(null);
    setConfusionDetected(false);
    setClassStarted(true);
    setHandoffNotice("Continuing from the homework recommendation.");
    setCurrentTopic(responseTopic);
    setCurrentConcept(responseConcept ?? null);
    setPendingClassResponse(null);
  }, [
    pendingClassResponse,
    curriculum,
    selectedChapterSlug,
    selectedGrade,
    setCurrentConcept,
    setCurrentTopic,
    setPendingClassResponse,
    studentLevel,
    teachingLanguage,
  ]);

  useEffect(() => {
    if (!handoffNotice) return undefined;

    const timeoutId = window.setTimeout(() => setHandoffNotice(null), 4800);
    return () => window.clearTimeout(timeoutId);
  }, [handoffNotice]);

  function changeChapter(slug: ChapterSlug) {
    setSelectedChapterSlug(slug);
    setConceptIndex(0);
    setCompletedConceptIds([]);
    setDiscussionTurns([]);
    resetRuntimeForNewSelection();
  }

  function changeStudentLevel(nextLevel: StudentLevel) {
    setStudentLevel(nextLevel);
    resetRuntimeForNewSelection();
  }

  function beginClassroom() {
    setClassStarted(true);
    resetRuntimeForNewSelection();
  }

  function selectConcept(index: number) {
    setConceptIndex(index);
    resetRuntimeForNewSelection();
  }

  function previousConcept() {
    setConceptIndex((current) => Math.max(0, current - 1));
    resetRuntimeForNewSelection();
  }

  function nextConcept() {
    setCompletedConceptIds((current) => {
      if (current.includes(currentConcept.id)) return current;
      return [...current, currentConcept.id];
    });
    setConceptIndex((current) => Math.min(chapter.concepts.length - 1, current + 1));
    resetRuntimeForNewSelection();
  }

  function focusQuestionInput() {
    window.setTimeout(() => document.getElementById("classroom-question-input")?.focus(), 0);
  }

  function useQuestionPrompt(prompt: string) {
    setQuestionText(prompt);
    focusQuestionInput();
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const question = questionText.trim();
    if (!question || loadingAnswer) return;

    setLoadingAnswer(true);

    try {
      const confusionDetected = /\b(confused|stuck|lost|again|repeat|slow|why|not understand|did not understand|don't understand|doubt)\b/i.test(question);
      const spokenAnswer = confusionDetected
        ? `Good catch. Let us make ${currentConcept.shortTitle} smaller. ${currentConcept.intuition}`
        : `Good question. Keep this idea in mind: ${currentConcept.summary}`;
      const turnId = Date.now();

      setDiscussionTurns((current) => [
        ...current,
        { id: `student-${turnId}`, role: "student", content: question },
        { id: `tutor-${turnId}`, role: "tutor", content: spokenAnswer },
      ]);
      setQuestionTimeline(buildQuestionTimeline(chapter, currentConcept, question));
      setConfusionDetected(confusionDetected);
      setQuestionText("");
    } finally {
      setLoadingAnswer(false);
    }
  }

  if (curriculumLoading) {
    return <main className="min-h-[calc(100vh-4rem)] bg-slate-50 p-8 text-slate-700">Loading Knowledge Factory curriculum...</main>;
  }

  if (curriculumError || !curriculum || !selectedChapter || !chapter) {
    return (
      <main className="min-h-[calc(100vh-4rem)] bg-slate-50 p-8 text-red-800">
        <h1 className="text-xl font-semibold">Knowledge Factory curriculum unavailable</h1>
        <p className="mt-2 max-w-2xl text-sm">{curriculumError || "The backend returned no Knowledge Factory curriculum."}</p>
        <p className="mt-2 text-sm">Start the updated backend and verify its Firestore credentials, then reload this page.</p>
      </main>
    );
  }

  if (!classAllowed) {
    return (
      <main className="min-h-[calc(100vh-4rem)] bg-slate-50">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <UpgradeNotice
            title={examMode === "jee" ? "JEE class mode needs a subscription" : "Subscribe to continue after Chapter 1"}
            description={
              examMode === "jee"
                ? "JEE class mode is included in JEE Pro."
                : `Chapter 1 is free. Chapter ${selectedChapterIndex + 1}: ${selectedChapter.title} requires an active grade subscription.`
            }
            recommendedPlan={examMode === "jee" ? "jee_pro" : "cbse_pro"}
          />
          <div className="mt-4 flex flex-wrap gap-3">
            {examMode === "cbse" ? (
              <button
                type="button"
                onClick={() => changeChapter(curriculum.chapters[0].slug)}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Open free Chapter 1
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => onNavigate("subscription")}
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            >
              View subscription
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (!classStarted) {
    return (
      <main className="min-h-[calc(100vh-4rem)] bg-[#f6f8fb] text-slate-950">
        <div className="mx-auto flex min-h-[calc(100vh-8rem)] w-full max-w-5xl items-center px-4 py-8 sm:px-6">
          <section className="w-full rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-slate-200/70 sm:p-7">
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">MathVerse Classroom</p>
                <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-normal text-slate-950 sm:text-4xl">
                  Start a synchronized {examMode.toUpperCase()} math class.
                </h1>
                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
                  The tutor voice, written board, diagrams, graph plots, highlights, and progress all run from one lesson
                  timeline, so the explanation and board stay together.
                </p>
              </div>

              <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
                <p className="text-sm font-semibold text-blue-950">Selected chapter</p>
                <p className="mt-2 text-2xl font-semibold text-blue-950">{selectedChapter.title}</p>
                <p className="mt-2 text-sm leading-6 text-blue-900">
                  {selectedChapterIndex === 0 && examMode === "cbse"
                    ? "This chapter is available on the free plan."
                    : "Plan access is checked before the classroom opens."}
                </p>
              </div>
            </div>

            <div className="mt-7 grid gap-4 lg:grid-cols-3">
              <label className="block">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Grade</span>
                <select
                  value={selectedGrade}
                  onChange={(event) => setSelectedGrade(Number(event.target.value) as ClassroomGrade)}
                  className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                >
                  {gradeOptions.map((grade) => (
                    <option key={grade} value={grade}>
                      Grade {grade}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Teaching language</span>
                <select
                  value={teachingLanguage}
                  onChange={(event) => setTeachingLanguage(event.target.value as TeachingLanguage)}
                  className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                >
                  {TEACHING_LANGUAGES.map((language) => (
                    <option key={language.value} value={language.value}>
                      {language.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Chapter</span>
                <select
                  value={selectedChapterSlug}
                  onChange={(event) => changeChapter(event.target.value as ChapterSlug)}
                  className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                >
                  {curriculum.chapters.map((chapterOption, index) => (
                    <option key={chapterOption.slug} value={chapterOption.slug}>
                      Chapter {index + 1}: {chapterOption.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {STUDENT_LEVELS.map((level) => (
                <button
                  key={level.value}
                  type="button"
                  onClick={() => changeStudentLevel(level.value)}
                  className={`rounded-lg border p-4 text-left transition ${
                    studentLevel === level.value
                      ? "border-blue-300 bg-blue-50 text-blue-950 ring-4 ring-blue-100"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <span className="block text-sm font-semibold">{level.label}</span>
                  <span className="mt-1 block text-xs leading-5 opacity-80">{level.description}</span>
                </button>
              ))}
            </div>

            <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm leading-6 text-slate-500">
                This classroom is loaded from the published Knowledge Factory package.
              </p>
              <button
                type="button"
                onClick={beginClassroom}
                className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              >
                Start Class
              </button>
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <ClassroomLayout
      header={
        <div className="space-y-3">
          <ChapterOverview chapter={chapter} chapterProgress={chapterProgress} studentLevel={studentLevel} />
          {handoffNotice ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900">
              {handoffNotice}
            </div>
          ) : null}
        </div>
      }
      sidebar={
        <div className="space-y-4">
          <section className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Class settings</p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">Runtime source</h2>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Synced</span>
            </div>

            <label className="mt-4 block">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Chapter</span>
              <select
                value={selectedChapterSlug}
                onChange={(event) => changeChapter(event.target.value as ChapterSlug)}
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              >
                {curriculum.chapters.map((chapterOption, index) => (
                  <option key={chapterOption.slug} value={chapterOption.slug}>
                    {index + 1}. {chapterOption.title}
                  </option>
                ))}
              </select>
            </label>

            <label className="mt-4 block">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Language</span>
              <select
                value={teachingLanguage}
                onChange={(event) => setTeachingLanguage(event.target.value as TeachingLanguage)}
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              >
                {TEACHING_LANGUAGES.map((language) => (
                  <option key={language.value} value={language.value}>
                    {language.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="mt-4 block">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Student level</span>
              <select
                value={studentLevel}
                onChange={(event) => changeStudentLevel(event.target.value as StudentLevel)}
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              >
                {STUDENT_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setConceptIndex(0);
                  setCompletedConceptIds([]);
                  resetRuntimeForNewSelection();
                  timelineRuntime.replay();
                }}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Restart
              </button>
              <button
                type="button"
                onClick={() => onNavigate("homework")}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Homework
              </button>
            </div>
          </section>

          <ConceptNavigator
            concepts={chapter.concepts}
            currentIndex={conceptIndex}
            completedConceptIds={completedConceptIds}
            onSelectConcept={selectConcept}
          />
        </div>
      }
      whiteboard={
        <SynchronizedWhiteboard
          chapterTitle={chapter.title}
          conceptTitle={activeTimeline.conceptTitle}
          events={timelineRuntime.boardEvents}
          highlightedTargetId={timelineRuntime.highlightedTargetId}
          isPlaying={timelineRuntime.isPlaying && !timelineRuntime.isPaused}
        />
      }
      tutor={
        <TutorPanel
          tutorLabel={tutorLabel}
          conceptTitle={activeTimeline.conceptTitle}
          currentStepLabel={currentStepLabel}
          currentSpeech={timelineRuntime.currentSpeech}
          isSpeaking={timelineRuntime.isSpeaking}
          isPaused={timelineRuntime.isPaused}
          loadingAnswer={loadingAnswer}
          questionText={questionText}
          discussionTurns={discussionTurns}
          confusionDetected={confusionDetected}
          onQuestionChange={setQuestionText}
          onQuestionSubmit={submitQuestion}
          onUsePrompt={useQuestionPrompt}
        />
      }
      controls={
        <ClassroomControls
          isPlaying={timelineRuntime.isPlaying}
          isPaused={timelineRuntime.isPaused}
          canPrevious={conceptIndex > 0}
          canNext={conceptIndex < chapter.concepts.length - 1}
          lessonProgress={timelineRuntime.progress}
          onTogglePlay={timelineRuntime.togglePlay}
          onPreviousConcept={previousConcept}
          onNextConcept={nextConcept}
          onReplay={timelineRuntime.replay}
          onAskQuestion={focusQuestionInput}
        />
      }
    />
  );
}
