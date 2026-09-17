import type {
  ChapterLesson,
  LessonConcept,
  LessonEvent,
} from "./lessonTimeline";

export type KnowledgeFactoryEntity = Record<string, unknown>;

export type KnowledgeFactoryPackage = {
  concepts?: KnowledgeFactoryEntity[];
  formulas?: KnowledgeFactoryEntity[];
  examples?: KnowledgeFactoryEntity[];
  exercises?: KnowledgeFactoryEntity[];
  figures?: KnowledgeFactoryEntity[];
  sections?: KnowledgeFactoryEntity[];
};

type KnowledgeFactoryChapter = {
  id: string;
  slug: string;
  number?: number | string | null;
  title: string;
  concepts?: KnowledgeFactoryEntity[];
};

function text(value: unknown): string {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function firstText(entity: KnowledgeFactoryEntity | undefined, keys: string[]): string {
  for (const key of keys) {
    const value = text(entity?.[key]);
    if (value) return value;
  }
  return "";
}

function cleanSourceText(value: string, maxLength = 220): string {
  const compact = value
    .replace(/\{[^{}]{0,80}\}/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return compact.length > maxLength ? `${compact.slice(0, maxLength - 1).trim()}...` : compact;
}

function toMathLatex(value: string): string {
  return value
    .replace(/−/g, "-")
    .replace(/≤/g, "\\leq ")
    .replace(/≥/g, "\\geq ")
    .replace(/\bsqrt\s*\(([^()]+)\)/gi, "\\sqrt{$1}")
    .replace(/\b(sqrt)\s+([A-Za-z0-9]+)/gi, "\\sqrt{$2}")
    .replace(/([A-Za-z0-9]+)\^([A-Za-z0-9]+)/g, "$1^{$2}")
    .replace(/\b([A-Za-z0-9]+)\/([A-Za-z0-9]+)\b/g, "\\frac{$1}{$2}")
    .replace(/\btheta\b/gi, "\\theta")
    .trim();
}

function looksMathematical(value: string): boolean {
  return /(?:=|\^|\/|sqrt|\\frac|\\sqrt|≤|≥|<=|>=|\b(?:sin|cos|tan)\b)/i.test(value);
}

function math(value: string): string {
  return `$$${toMathLatex(value)}$$`;
}

function equationSteps(value: string): string[] {
  const normalized = value.replace(/−/g, "-").replace(/\s+/g, " ").trim();
  const match = normalized.match(/^2\s*x\s*\+\s*3\s*=\s*11$/i);
  if (match) return ["2x + 3 = 11", "2x = 8", "x = 4"];

  const linear = normalized.match(/^([+-]?\d+)\s*x\s*([+-])\s*(\d+)\s*=\s*([+-]?\d+)$/i);
  if (!linear) return [];
  const coefficient = Number(linear[1]);
  const constant = Number(linear[3]) * (linear[2] === "+" ? 1 : -1);
  const result = Number(linear[4]);
  const isolated = result - constant;
  if (!Number.isFinite(coefficient) || coefficient === 0) return [];
  return [normalized, `${coefficient}x = ${isolated}`, `x = ${isolated / coefficient}`];
}

function conceptFromPackage(
  chapter: KnowledgeFactoryChapter,
  concept: KnowledgeFactoryEntity,
  index: number,
  packageData: KnowledgeFactoryPackage,
): LessonConcept {
  const title = firstText(concept, ["name", "title"]) || `Concept ${index + 1}`;
  const id = firstText(concept, ["id"]) || `${chapter.slug}-concept-${index + 1}`;
  const formula = packageData.formulas?.find((item) => text(item.section_number) === text(concept.section_number));
  const example = packageData.examples?.[index] ?? packageData.examples?.[0];
  const exercise = packageData.exercises?.[index] ?? packageData.exercises?.[0];
  const formulaText = firstText(formula, ["expression", "formula", "latex"]);
  const exampleText = firstText(example, ["content", "problem", "title"]);
  const exerciseQuestions = Array.isArray(exercise?.questions) ? exercise.questions : [];
  const practiceText = firstText((exerciseQuestions[index] as KnowledgeFactoryEntity | undefined) ?? exercise, ["question", "prompt", "text"]);
  const explanation = cleanSourceText(firstText(concept, ["explanation", "description", "definition", "name"]));
  const solutionSource = exampleText || formulaText || practiceText;
  const steps = equationSteps(solutionSource);

  const events: LessonEvent[] = [
    { type: "speak", text: `Let us make ${title} simple. I will show the idea, then we will use it.` },
    { type: "write", id: `${id}-title`, kind: "heading", content: title },
    { type: "speak", text: explanation ? `${explanation}. Notice the key idea on the board.` : `This is the key idea behind ${title}.` },
    { type: "write", id: `${id}-explanation`, kind: "note", content: explanation || `Key idea: ${title}.` },
  ];

  if (formulaText) {
    events.push(
      { type: "speak", text: "Here is the rule we will use. Keep it visible while we work." },
      { type: "write", id: `${id}-formula`, kind: "equation", content: math(formulaText) },
    );
  }

  if (exampleText) {
    events.push(
      { type: "speak", text: "Now let us see one worked example. I will take it one step at a time." },
      { type: "write", id: `${id}-example-label`, kind: "example", content: "Worked example" },
      {
        type: "write",
        id: `${id}-example`,
        kind: looksMathematical(exampleText) ? "equation" : "example",
        content: looksMathematical(exampleText) ? math(exampleText) : cleanSourceText(exampleText),
      },
    );
  }

  if (steps.length) {
    events.push(
      { type: "speak", text: "We keep both sides balanced, then isolate the unknown." },
      ...steps.map((step, stepIndex) => ({
        type: "write" as const,
        id: `${id}-step-${stepIndex}`,
        kind: "equation" as const,
        content: math(step),
      })),
    );
  }

  if (practiceText) {
    events.push(
      { type: "speak", text: "Your turn. Try this question, and explain the first step out loud." },
      { type: "write", id: `${id}-practice-label`, kind: "question", content: "Try it yourself" },
      { type: "write", id: `${id}-practice`, kind: "question", content: cleanSourceText(practiceText, 260) },
    );
  }

  const figure = packageData.figures?.[index] ?? packageData.figures?.[0];
  const figureType = firstText(figure, ["figure_type", "type", "caption"]).toLowerCase();
  const shape = figureType.includes("circle")
    ? "circle"
    : figureType.includes("rectangle")
      ? "rectangle"
      : figureType.includes("triangle")
        ? "triangle"
        : null;
  if (shape) {
    events.push({
      type: "speak",
      text: "Look at the shape as we connect the picture to the idea.",
    });
    events.push({
      type: "draw",
      id: `${id}-figure`,
      drawing: {
        kind: "geometry",
        shape,
        labels: Array.isArray(figure?.labels) ? figure.labels.map(text).filter(Boolean).slice(0, 3) : undefined,
        annotations: [cleanSourceText(firstText(figure, ["caption", "description"]), 100)].filter(Boolean),
      },
    });
  }

  events.push({ type: "pause", durationMs: 650 });

  return {
    id,
    title,
    shortTitle: title,
    summary: explanation || `A focused lesson on ${title}.`,
    intuition: explanation || `We will build ${title} step by step.`,
    checkQuestion: practiceText || `Explain the main idea of ${title} in your own words.`,
    events,
  };
}

export function presentKnowledgeFactoryChapter(
  chapter: KnowledgeFactoryChapter,
  grade: number,
  packageData: KnowledgeFactoryPackage = {},
): ChapterLesson {
  const concepts = (chapter.concepts ?? []).map((concept, index) =>
    conceptFromPackage(chapter, concept, index, packageData),
  );
  const safeConcepts = concepts.length
    ? concepts
    : [
        {
          id: `${chapter.slug}-overview`,
          title: chapter.title,
          shortTitle: chapter.title,
          summary: `Published Knowledge Factory material for ${chapter.title}.`,
          intuition: `We will build ${chapter.title} step by step.`,
          checkQuestion: `What is the central idea of ${chapter.title}?`,
          events: [
            { type: "speak", text: `Let us begin ${chapter.title}. I will show the main idea first.` },
            { type: "write", kind: "heading", content: chapter.title },
            { type: "write", kind: "note", content: "Published Knowledge Factory lesson content." },
            { type: "pause", durationMs: 650 },
          ],
        },
      ];

  return {
    slug: chapter.slug,
    title: chapter.title,
    grade,
    overview: {
      about: `Published lesson material for ${chapter.title}.`,
      whyItMatters: "We will connect the rule to an example and then let you practise.",
      mainConcepts: safeConcepts.map((concept) => concept.title),
      realWorldExamples: [],
    },
    concepts: safeConcepts,
  };
}
