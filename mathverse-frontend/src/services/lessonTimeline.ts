import type { TeachingLanguage } from "./api";
import { presentKnowledgeFactoryChapter, type KnowledgeFactoryPackage } from "./knowledgeFactoryPresenter";

export type StudentLevel = "foundation" | "standard" | "advanced";

export type BoardItemKind = "heading" | "note" | "equation" | "example" | "question" | "summary";

export type DrawingInstruction =
  | {
      kind: "number-line";
      min: number;
      max: number;
      points?: Array<{ value: number; label: string; tone?: "blue" | "green" | "amber" }>;
      intervals?: Array<{ from: number; to: number; label: string }>;
    }
  | {
      kind: "coordinate-plane";
      points?: Array<{ x: number; y: number; label: string }>;
      segments?: Array<{ from: [number, number]; to: [number, number]; label?: string }>;
    }
  | {
      kind: "geometry";
      shape: "triangle" | "circle" | "rectangle";
      labels?: string[];
      annotations?: string[];
    }
  | {
      kind: "arrow";
      from: string;
      to: string;
      label?: string;
    }
  | {
      kind: "area-model";
      rows: number;
      cols: number;
      label: string;
    };

export type LessonEvent =
  | { type: "speak"; text: string; durationMs?: number; id?: string }
  | { type: "write"; content: string; kind?: BoardItemKind; id?: string; durationMs?: number }
  | { type: "draw"; drawing: DrawingInstruction; id?: string; durationMs?: number }
  | { type: "plot"; expression: string; id?: string; title?: string; durationMs?: number }
  | { type: "highlight"; targetId: string; durationMs?: number }
  | { type: "pause"; durationMs: number };

export type LessonConcept = {
  id: string;
  title: string;
  shortTitle: string;
  summary: string;
  intuition: string;
  checkQuestion: string;
  events: LessonEvent[];
};

export type ChapterLesson = {
  slug: string;
  title: string;
  grade: number;
  overview: {
    about: string;
    whyItMatters: string;
    mainConcepts: string[];
    realWorldExamples: string[];
  };
  concepts: LessonConcept[];
};

export type KnowledgeFactoryCurriculumPayload = {
  source?: string;
  document_id: string;
  schema_version?: string;
  metadata: Record<string, unknown>;
  chapters: Array<{
    id: string;
    slug: string;
    number?: number | string | null;
    title: string;
    concepts?: Array<Record<string, unknown>>;
  }>;
  knowledge_package?: KnowledgeFactoryPackage;
};

export type TimelineRequest = {
  chapterSlug: string;
  grade: number;
  studentLevel: StudentLevel;
  teachingLanguage: TeachingLanguage;
};

export type ConceptTimelineRequest = {
  chapter: ChapterLesson;
  conceptIndex: number;
  includeOverview?: boolean;
};

export type LessonTimeline = {
  id: string;
  chapterTitle: string;
  conceptTitle: string;
  events: LessonEvent[];
};

export interface LessonTimelineService {
  loadChapter(request: TimelineRequest): ChapterLesson;
  getConceptTimeline(request: ConceptTimelineRequest): LessonTimeline;
  answerStudentQuestion(input: {
    chapter: ChapterLesson;
    concept: LessonConcept;
    question: string;
    studentLevel: StudentLevel;
  }): QuestionResponse;
}

export function chapterLessonFromKnowledgeFactory(
  chapter: KnowledgeFactoryCurriculumPayload["chapters"][number],
  grade: number,
  packageData: KnowledgeFactoryPackage = {},
): ChapterLesson {
  return presentKnowledgeFactoryChapter(chapter, grade, packageData);
}

export const CLASSROOM_GRADES = [10, 11, 12] as const;

export type ClassroomGrade = (typeof CLASSROOM_GRADES)[number];

export const TEACHING_LANGUAGES: Array<{ value: TeachingLanguage; label: string; speechLang: string }> = [
  { value: "en-IN", label: "English (India)", speechLang: "en-IN" },
  { value: "hi-IN", label: "Hindi", speechLang: "hi-IN" },
  { value: "gu-IN", label: "Gujarati", speechLang: "gu-IN" },
];

const conceptMap: Record<string, Array<Omit<LessonConcept, "events">>> = {
  real_numbers: [
    {
      id: "euclid-division-lemma",
      title: "Euclid's Division Lemma",
      shortTitle: "Division Lemma",
      summary: "Any positive integer can be split into divisor, quotient, and remainder.",
      intuition: "It is the math version of sharing objects equally and counting what is left.",
      checkQuestion: "If 26 is divided by 5, what are the quotient and remainder?",
    },
    {
      id: "hcf-by-euclid",
      title: "Finding HCF with Euclid's Algorithm",
      shortTitle: "HCF Algorithm",
      summary: "Repeatedly divide and use the remainder until the remainder becomes zero.",
      intuition: "The last non-zero remainder is the largest common measuring stick.",
      checkQuestion: "Find the HCF of 65 and 117 using Euclid's algorithm.",
    },
    {
      id: "irrational-numbers",
      title: "Irrational Numbers",
      shortTitle: "Irrationals",
      summary: "Some numbers cannot be written as a ratio of two integers.",
      intuition: "Their decimal expansion keeps going without settling into a repeating pattern.",
      checkQuestion: "Why is sqrt(2) not a rational number?",
    },
    {
      id: "decimal-expansions",
      title: "Decimal Expansions",
      shortTitle: "Decimals",
      summary: "Prime factors of the denominator decide whether a decimal terminates.",
      intuition: "Denominators made from only 2s and 5s fit neatly into powers of 10.",
      checkQuestion: "Will 7/40 have a terminating decimal expansion?",
    },
  ],
  polynomials: [
    {
      id: "polynomial-basics",
      title: "Polynomial Language",
      shortTitle: "Basics",
      summary: "Terms, coefficients, variables, and degree help us describe expressions clearly.",
      intuition: "A polynomial is like a recipe made from powers of a variable.",
      checkQuestion: "What is the degree of 3x^2 - 5x + 2?",
    },
    {
      id: "zeros-of-polynomials",
      title: "Zeros of a Polynomial",
      shortTitle: "Zeros",
      summary: "A zero is an input that makes the polynomial value become 0.",
      intuition: "On a graph, zeros are the points where the curve touches or crosses the x-axis.",
      checkQuestion: "Is x = 2 a zero of p(x) = x - 2?",
    },
    {
      id: "quadratic-graph-shape",
      title: "Quadratic Graph Shape",
      shortTitle: "Parabolas",
      summary: "A quadratic polynomial makes a U-shaped graph called a parabola.",
      intuition: "The graph bends because x^2 grows on both sides of zero.",
      checkQuestion: "How many zeros can a quadratic polynomial have at most?",
    },
  ],
  coordinate_geometry: [
    {
      id: "cartesian-plane",
      title: "Reading the Cartesian Plane",
      shortTitle: "Plane",
      summary: "Every point is located by an x-coordinate and a y-coordinate.",
      intuition: "It works like a city grid: move left-right first, then up-down.",
      checkQuestion: "Where is the point (3, -2) placed on the coordinate plane?",
    },
    {
      id: "distance-formula",
      title: "Distance Formula",
      shortTitle: "Distance",
      summary: "The distance formula comes from the Pythagorean theorem.",
      intuition: "Horizontal and vertical changes make a right triangle between two points.",
      checkQuestion: "Find the distance between (0, 0) and (3, 4).",
    },
    {
      id: "section-formula",
      title: "Section Formula",
      shortTitle: "Section",
      summary: "The section formula finds a point that divides a line segment in a given ratio.",
      intuition: "It is a weighted balance point between two coordinates.",
      checkQuestion: "What is the midpoint of (2, 4) and (6, 8)?",
    },
  ],
  triangles: [
    {
      id: "similar-triangles",
      title: "Similar Triangles",
      shortTitle: "Similarity",
      summary: "Similar triangles have the same shape even when their sizes differ.",
      intuition: "They are like resized photos: angles stay equal and sides scale together.",
      checkQuestion: "If two triangles are similar, what happens to corresponding angles?",
    },
    {
      id: "basic-proportionality",
      title: "Basic Proportionality Theorem",
      shortTitle: "BPT",
      summary: "A line parallel to one side of a triangle divides the other two sides proportionally.",
      intuition: "Parallel slicing keeps the smaller triangle in the same shape as the big one.",
      checkQuestion: "What condition lets us use the Basic Proportionality Theorem?",
    },
    {
      id: "pythagoras-theorem",
      title: "Pythagoras Theorem",
      shortTitle: "Pythagoras",
      summary: "In a right triangle, the square on the hypotenuse equals the sum of the squares on the other two sides.",
      intuition: "The longest side balances the combined square areas of the two shorter sides.",
      checkQuestion: "If legs are 6 and 8, what is the hypotenuse?",
    },
  ],
  quadratic_equations: [
    {
      id: "quadratic-meaning",
      title: "What a Quadratic Equation Means",
      shortTitle: "Meaning",
      summary: "A quadratic equation has the highest power 2 and usually asks where an expression becomes zero.",
      intuition: "It often models situations that rise and fall, like a thrown ball.",
      checkQuestion: "Which part tells you x^2 - 5x + 6 = 0 is quadratic?",
    },
    {
      id: "factorisation-method",
      title: "Solving by Factorisation",
      shortTitle: "Factorisation",
      summary: "Break the quadratic into two linear factors, then use the zero product idea.",
      intuition: "If two numbers multiply to zero, at least one of them must be zero.",
      checkQuestion: "Solve x^2 - 5x + 6 = 0 by factorisation.",
    },
    {
      id: "quadratic-formula",
      title: "Quadratic Formula",
      shortTitle: "Formula",
      summary: "The formula solves any quadratic equation ax^2 + bx + c = 0.",
      intuition: "It is a reliable tool when factorisation is not obvious.",
      checkQuestion: "What does the discriminant b^2 - 4ac tell us?",
    },
  ],
};

const defaultConcepts: Array<Omit<LessonConcept, "events">> = [
  {
    id: "chapter-language",
    title: "The Big Idea",
    shortTitle: "Big Idea",
    summary: "We learn the language and central pattern of this chapter.",
    intuition: "Once the pattern is clear, formulas feel less like memory work.",
    checkQuestion: "What is the first idea you would explain to a friend?",
  },
  {
    id: "worked-examples",
    title: "Worked Examples",
    shortTitle: "Examples",
    summary: "We apply the idea slowly on representative problems.",
    intuition: "Examples turn definitions into actions you can repeat.",
    checkQuestion: "Which step of the example decides the method?",
  },
  {
    id: "student-check",
    title: "Mini Check",
    shortTitle: "Check",
    summary: "We test understanding with a small question before moving on.",
    intuition: "Short checks catch confusion early, before it becomes frustration.",
    checkQuestion: "Can you solve one similar problem on your own?",
  },
];

function normalizeChapter(slug: string) {
  return CBSE_GRADE_10_CHAPTERS.find((chapter) => chapter.slug === slug) ?? CBSE_GRADE_10_CHAPTERS[0];
}

function levelPhrase(studentLevel: StudentLevel) {
  if (studentLevel === "foundation") return "We will go slowly and keep every step visible.";
  if (studentLevel === "advanced") return "We will also look for shortcuts and patterns after the idea is clear.";
  return "We will keep the pace steady and focus on understanding first.";
}

function overviewForChapter(title: string, concepts: Array<Omit<LessonConcept, "events">>) {
  return {
    about: `${title} is about recognizing a small set of patterns and using them to solve problems without guessing.`,
    whyItMatters:
      "It matters because the same ideas show up in exams, measurements, graphs, finance, design, and everyday reasoning.",
    mainConcepts: concepts.map((concept) => concept.shortTitle),
    realWorldExamples: [
      "Sharing quantities equally and tracking what remains",
      "Reading graphs, maps, and visual data",
      "Checking whether an answer is reasonable before submitting it",
    ],
  };
}

function chapterDrawing(slug: string): DrawingInstruction {
  if (slug === "coordinate_geometry") {
    return {
      kind: "coordinate-plane",
      points: [
        { x: 0, y: 0, label: "O" },
        { x: 3, y: 4, label: "A(3,4)" },
      ],
      segments: [{ from: [0, 0], to: [3, 4], label: "distance" }],
    };
  }
  if (slug === "triangles") {
    return {
      kind: "geometry",
      shape: "triangle",
      labels: ["A", "B", "C"],
      annotations: ["same shape", "scaled sides", "equal angles"],
    };
  }
  if (slug === "polynomials" || slug === "quadratic_equations") {
    return {
      kind: "coordinate-plane",
      points: [
        { x: -2, y: 0, label: "zero" },
        { x: 2, y: 0, label: "zero" },
        { x: 0, y: -4, label: "turn" },
      ],
    };
  }
  return {
    kind: "number-line",
    min: 0,
    max: 12,
    points: [
      { value: 5, label: "divisor", tone: "blue" },
      { value: 10, label: "2 groups", tone: "green" },
      { value: 12, label: "remainder 2", tone: "amber" },
    ],
    intervals: [{ from: 0, to: 10, label: "equal groups" }],
  };
}

function conceptEvents(slug: string, chapterTitle: string, concept: Omit<LessonConcept, "events">, studentLevel: StudentLevel) {
  const safeTitle = concept.title;
  const events: LessonEvent[] = [
    {
      type: "speak",
      text: `Now let us start ${safeTitle}. ${levelPhrase(studentLevel)} First we build the idea, then we try one small check.`,
    },
    { type: "write", id: "concept-title", kind: "heading", content: safeTitle },
    { type: "write", id: "concept-summary", kind: "note", content: concept.summary },
    { type: "pause", durationMs: 450 },
    { type: "speak", text: `Simple intuition: ${concept.intuition}` },
    { type: "draw", id: "main-visual", drawing: chapterDrawing(slug), durationMs: 800 },
    { type: "highlight", targetId: "concept-summary", durationMs: 700 },
  ];

  if (slug === "polynomials" || slug === "quadratic_equations") {
    events.push(
      { type: "write", id: "equation-1", kind: "equation", content: "p(x) = x^2 - 4" },
      { type: "plot", id: "plot-1", title: "Where the graph meets the x-axis", expression: "y = x^2 - 4" },
      {
        type: "speak",
        text:
          "The visual clue is the x-axis crossing. The algebra clue is making the expression equal to zero. Both tell the same story.",
      },
      { type: "write", id: "equation-2", kind: "equation", content: "x^2 - 4 = 0 -> (x - 2)(x + 2) = 0" },
    );
  } else if (slug === "coordinate_geometry") {
    events.push(
      { type: "write", id: "equation-1", kind: "equation", content: "distance = sqrt((x2 - x1)^2 + (y2 - y1)^2)" },
      {
        type: "speak",
        text:
          "Notice the right triangle hidden between two points. The horizontal change and vertical change become the two shorter sides.",
      },
    );
  } else if (slug === "triangles") {
    events.push(
      { type: "write", id: "equation-1", kind: "equation", content: "corresponding angles equal -> sides in proportion" },
      {
        type: "speak",
        text:
          "For triangles, first ask whether the shape is the same. Once shape is fixed, side ratios become predictable.",
      },
    );
  } else {
    events.push(
      { type: "write", id: "equation-1", kind: "equation", content: "a = bq + r, where 0 <= r < b" },
      {
        type: "speak",
        text:
          "The remainder is always smaller than the divisor. That tiny rule is what makes the division process dependable.",
      },
      { type: "write", id: "example-1", kind: "example", content: "26 = 5 * 5 + 1" },
    );
  }

  events.push(
    { type: "pause", durationMs: 500 },
    {
      type: "speak",
      text:
        "Before we move on, try a tiny check. Do not rush the answer. Say the reason in one sentence.",
    },
    { type: "write", id: "mini-check", kind: "question", content: concept.checkQuestion },
  );

  return events;
}

function overviewEvents(chapter: ChapterLesson): LessonEvent[] {
  return [
    {
      type: "speak",
      text: `Welcome to ${chapter.title}. I will first give you the map of the chapter, then we will begin the first idea step by step.`,
    },
    { type: "write", id: "overview-title", kind: "heading", content: `${chapter.title}: chapter map` },
    { type: "write", id: "overview-about", kind: "note", content: chapter.overview.about },
    { type: "write", id: "overview-why", kind: "note", content: `Why it matters: ${chapter.overview.whyItMatters}` },
    {
      type: "write",
      id: "overview-concepts",
      kind: "summary",
      content: `Main concepts: ${chapter.overview.mainConcepts.join(", ")}`,
    },
    {
      type: "speak",
      text:
        "A useful way to learn this chapter is to connect every formula to a picture, an example, or a real situation.",
    },
    {
      type: "draw",
      id: "overview-visual",
      drawing: { kind: "arrow", from: "idea", to: "example", label: "idea -> example -> check" },
      durationMs: 700,
    },
    { type: "pause", durationMs: 500 },
  ];
}

function detectConfusion(question: string) {
  return /\b(confused|stuck|lost|again|repeat|slow|why|not understand|did not understand|don't understand|doubt)\b/i.test(
    question,
  );
}

export class LocalLessonTimelineService implements LessonTimelineService {
  loadChapter({ chapterSlug, grade, studentLevel }: TimelineRequest): ChapterLesson {
    const chapter = normalizeChapter(chapterSlug);
    const conceptTemplates = conceptMap[chapter.slug] ?? defaultConcepts;
    const concepts = conceptTemplates.map((concept) => ({
      ...concept,
      events: conceptEvents(chapter.slug, chapter.title, concept, studentLevel),
    }));

    return {
      slug: chapter.slug,
      title: chapter.title,
      grade,
      overview: overviewForChapter(chapter.title, conceptTemplates),
      concepts,
    };
  }

  getConceptTimeline({ chapter, conceptIndex, includeOverview = false }: ConceptTimelineRequest): LessonTimeline {
    const concept = chapter.concepts[Math.max(0, Math.min(conceptIndex, chapter.concepts.length - 1))];
    const events = includeOverview ? [...overviewEvents(chapter), ...concept.events] : concept.events;

    return {
      id: `${chapter.slug}-${concept.id}-${includeOverview ? "with-overview" : "concept"}`,
      chapterTitle: chapter.title,
      conceptTitle: concept.title,
      events,
    };
  }

  answerStudentQuestion({
    chapter,
    concept,
    question,
    studentLevel,
  }: {
    chapter: ChapterLesson;
    concept: LessonConcept;
    question: string;
    studentLevel: StudentLevel;
  }): QuestionResponse {
    const confusionDetected = detectConfusion(question);
    const spokenAnswer = confusionDetected
      ? `Good catch. Let us explain ${concept.shortTitle} in a smaller way. The heart of it is this: ${concept.intuition}`
      : `Nice question. For ${concept.shortTitle}, connect your question back to this main idea: ${concept.summary}`;

    const events: LessonEvent[] = [
      { type: "speak", text: spokenAnswer },
      {
        type: "write",
        id: "student-question",
        kind: "question",
        content: `Student question: ${question}`,
      },
      {
        type: "write",
        id: "adaptive-answer",
        kind: "note",
        content: confusionDetected
          ? "Smaller step: name the pattern first, then do only one operation at a time."
          : "Answer path: connect the question to the concept, then test it with a simple example.",
      },
      {
        type: "draw",
        id: "adaptive-visual",
        drawing:
          studentLevel === "advanced"
            ? { kind: "arrow", from: "pattern", to: "shortcut", label: "after understanding" }
            : { kind: "arrow", from: "what we know", to: "next small step", label: "slow it down" },
      },
      {
        type: "speak",
        text:
          "If this still feels cloudy, look only at the board line I highlighted. One clear line is better than ten rushed lines.",
      },
      { type: "highlight", targetId: "adaptive-answer", durationMs: 900 },
      { type: "write", id: "adaptive-check", kind: "question", content: concept.checkQuestion },
    ];

    return {
      spokenAnswer,
      confusionDetected,
      timeline: {
        id: `${chapter.slug}-${concept.id}-question-${Date.now()}`,
        chapterTitle: chapter.title,
        conceptTitle: `${concept.title}: student question`,
        events,
      },
    };
  }
}
