"use client";

import { useEffect, useMemo, useState } from "react";
import { StatCard } from "../components/StatCard";
import { getAttemptHistory, type AttemptRecord } from "../services/api";
import { useTutorStore } from "../store/useTutorStore";

const quickRevisionChapters = [
  {
    chapter: "Real Numbers",
    theorem: ["Euclid's division lemma: a = bq + r, 0 <= r < b.", "HCF x LCM = product of two positive integers."],
    formula: ["LCM(a,b) = ab / HCF(a,b)", "p/q terminates iff q has only factors 2 and/or 5 after reduction."],
    tips: ["Reduce fractions before checking decimal expansion.", "Use prime factorisation when HCF/LCM identity is not enough."],
  },
  {
    chapter: "Polynomials",
    theorem: ["Remainder theorem idea: value at x = a gives remainder for division by x - a.", "Zero of polynomial means p(a) = 0."],
    formula: ["For ax^2 + bx + c: sum of zeroes = -b/a.", "Product of zeroes = c/a."],
    tips: ["Always compare coefficients after writing polynomial in standard form.", "Substitute to verify a claimed zero."],
  },
  {
    chapter: "Pair of Linear Equations",
    theorem: ["Two lines intersect, are parallel, or coincide depending on coefficient ratios."],
    formula: ["a1/a2 != b1/b2: unique solution.", "a1/a2 = b1/b2 != c1/c2: no solution.", "a1/a2 = b1/b2 = c1/c2: infinitely many solutions."],
    tips: ["Keep equations in a1x + b1y + c1 = 0 form before comparing.", "Graph meaning helps avoid ratio mistakes."],
  },
  {
    chapter: "Quadratic Equations",
    theorem: ["A quadratic can have two, one, or no real roots based on discriminant."],
    formula: ["D = b^2 - 4ac", "x = (-b ± √D) / 2a"],
    tips: ["Check if factorisation is easy before using formula.", "Use D to predict nature of roots first."],
  },
  {
    chapter: "Arithmetic Progressions",
    theorem: ["In an AP, consecutive terms have the same difference."],
    formula: ["a_n = a + (n - 1)d", "S_n = n/2 [2a + (n - 1)d]"],
    tips: ["Identify a, d, n before substitution.", "For word problems, translate term number carefully."],
  },
  {
    chapter: "Triangles",
    theorem: ["Basic Proportionality Theorem.", "AA, SAS, and SSS similarity criteria.", "Pythagoras theorem."],
    formula: ["If DE || BC, then AD/DB = AE/EC.", "In right triangle: hypotenuse^2 = side1^2 + side2^2."],
    tips: ["Mark corresponding vertices in the same order.", "Draw the figure before writing ratios."],
  },
  {
    chapter: "Coordinate Geometry",
    theorem: ["Distance, section, and area formulas connect geometry to coordinates."],
    formula: ["Distance = √((x2-x1)^2 + (y2-y1)^2)", "Midpoint = ((x1+x2)/2, (y1+y2)/2)", "Area triangle = 1/2 |x1(y2-y3)+x2(y3-y1)+x3(y1-y2)|"],
    tips: ["Plot rough positions first.", "Use absolute value in area formula."],
  },
  {
    chapter: "Introduction to Trigonometry",
    theorem: ["Trigonometric ratios depend on angle, not triangle size."],
    formula: ["sin θ = opposite/hypotenuse", "cos θ = adjacent/hypotenuse", "tan θ = opposite/adjacent", "sin^2 θ + cos^2 θ = 1"],
    tips: ["Name opposite and adjacent relative to the angle.", "Memorize standard values for 0°, 30°, 45°, 60°, 90°."],
  },
  {
    chapter: "Applications of Trigonometry",
    theorem: ["Heights and distances use right triangles formed from line of sight."],
    formula: ["tan θ = height / distance", "sin θ and cos θ when hypotenuse is involved."],
    tips: ["Draw the ground line and vertical height first.", "Angles of elevation/depression are measured from horizontal."],
  },
  {
    chapter: "Circles",
    theorem: ["Tangent at any point of a circle is perpendicular to the radius through point of contact.", "Tangents from an external point are equal."],
    formula: ["If OP is radius and tangent touches at P, OP ⟂ tangent.", "From external A: AP = AQ."],
    tips: ["Always draw radius to point of contact.", "For parallel tangents, use endpoints of a diameter."],
  },
  {
    chapter: "Constructions",
    theorem: ["Constructions rely on perpendicular bisectors, angle bisectors, similar triangles, and tangents."],
    formula: ["Scale factor = required ratio / original ratio."],
    tips: ["Use compass arcs carefully.", "Write construction steps in order: draw base, locate points, join, verify."],
  },
  {
    chapter: "Areas Related to Circles",
    theorem: ["Sector and segment areas come from fraction of full circle."],
    formula: ["Area circle = πr^2", "Circumference = 2πr", "Area sector = θ/360 × πr^2", "Arc length = θ/360 × 2πr"],
    tips: ["Check whether angle is in degrees.", "Segment area usually means sector minus triangle."],
  },
  {
    chapter: "Surface Areas and Volumes",
    theorem: ["Composite solids are solved by adding visible surface areas and matching volumes."],
    formula: ["CSA cylinder = 2πrh", "Volume cylinder = πr^2h", "Volume cone = 1/3πr^2h", "Volume sphere = 4/3πr^3"],
    tips: ["Draw the solid and mark hidden/common faces.", "Keep units squared for area and cubed for volume."],
  },
  {
    chapter: "Statistics",
    theorem: ["Mean, median, and mode summarize grouped data differently."],
    formula: ["Mean = Σfixi / Σfi", "Mode = l + ((f1-f0)/(2f1-f0-f2))h", "Median = l + ((n/2-cf)/f)h"],
    tips: ["Make a clean frequency table.", "Identify modal/median class before substituting."],
  },
  {
    chapter: "Probability",
    theorem: ["Probability of an event = favorable outcomes / total equally likely outcomes."],
    formula: ["P(E) = n(E)/n(S)", "P(not E) = 1 - P(E)"],
    tips: ["List sample space for small problems.", "Check outcomes are equally likely."],
  },
];

export default function Progress() {
  const sessionId = useTutorStore((state) => state.session_id);
  const stats = useTutorStore((state) => state.stats);
  const [attempts, setAttempts] = useState<AttemptRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [revisionChapter, setRevisionChapter] = useState(quickRevisionChapters[0].chapter);

  useEffect(() => {
    let cancelled = false;

    async function loadAttempts() {
      try {
        const history = await getAttemptHistory(sessionId);
        if (!cancelled) {
          setAttempts(history);
          setHistoryError(null);
        }
      } catch {
        if (!cancelled) {
          setHistoryError("Saved attempt history is unavailable. Showing local session data.");
        }
      }
    }

    void loadAttempts();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const accuracy = stats.total ? Math.round((stats.correct / stats.total) * 100) : 0;
  const savedStats = useMemo(() => {
    const total = attempts.filter((attempt) => attempt.correct !== null && attempt.correct !== undefined).length;
    const correct = attempts.filter((attempt) => attempt.correct === true).length;
    const byMistake: Record<string, number> = {};
    const byTopic: Record<string, number> = {};
    const byPattern: Record<string, number> = {};

    attempts.forEach((attempt) => {
      if (attempt.mistake_type) {
        byMistake[attempt.mistake_type] = (byMistake[attempt.mistake_type] || 0) + 1;
      }
      if (attempt.correct === false && attempt.topic) {
        byTopic[attempt.topic] = (byTopic[attempt.topic] || 0) + 1;
      }
      if (attempt.correct === false && attempt.pattern) {
        byPattern[attempt.pattern] = (byPattern[attempt.pattern] || 0) + 1;
      }
    });

    return { total, correct, wrong: total - correct, byMistake, byTopic, byPattern };
  }, [attempts]);

  const effective = savedStats.total > stats.total ? savedStats : {
    total: stats.total,
    correct: stats.correct,
    wrong: stats.wrong,
    byMistake: stats.byMistake,
    byTopic: stats.byTopic,
    byPattern: stats.byPattern,
  };
  const effectiveAccuracy = effective.total ? Math.round((effective.correct / effective.total) * 100) : accuracy;
  const mistakes = Object.entries(effective.byMistake);
  const topics = Object.entries(effective.byTopic);
  const patterns = Object.entries(effective.byPattern);
  const selectedRevision = quickRevisionChapters.find((item) => item.chapter === revisionChapter) || quickRevisionChapters[0];
  const predictedScore = Math.min(300, Math.round(effectiveAccuracy * 3));
  const sevenDayPlan = [
    "Day 1: Relearn the weakest concept using board examples.",
    "Day 2: Solve 20 easy questions without timer.",
    "Day 3: Fix the top mistake type with step-by-step review.",
    "Day 4: Attempt 20 medium questions with explanations.",
    "Day 5: Run a 30-minute timed mixed practice set.",
    "Day 6: Revise formulas, shortcuts, and saved notes.",
    "Day 7: Take a timed test and compare accuracy.",
  ];

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Accuracy" value={`${effectiveAccuracy}%`} />
        <StatCard label="Answered" value={`${effective.total}`} />
        <StatCard label="Correct" value={`${effective.correct}`} />
        <StatCard label="Wrong" value={`${effective.wrong}`} />
      </section>

      {historyError && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{historyError}</div>}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">Accuracy chart</h2>
          <div className="mt-4 h-4 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-emerald-500" style={{ width: `${effectiveAccuracy}%` }} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">Mistake types breakdown</h2>
          <div className="mt-4 space-y-3">
            {mistakes.length ? (
              mistakes.map(([type, count]) => (
                <div key={type} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                  <span>{type}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No mistakes recorded yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Score Prediction</h2>
          <p className="mt-4 text-4xl font-semibold text-slate-950">{predictedScore}</p>
          <p className="mt-2 text-sm text-slate-500">Estimated out of 300 from current accuracy. This becomes stronger as more timed attempts are logged.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">7-Day Improvement Plan</h2>
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {sevenDayPlan.map((item) => (
              <div key={item} className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-950">Chapter Quick Revision</h2>
            <p className="mt-1 text-sm text-slate-500">Theorems, formulas, and exam tips for fast review.</p>
          </div>
          <select
            value={revisionChapter}
            onChange={(event) => setRevisionChapter(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-blue-400"
          >
            {quickRevisionChapters.map((item) => (
              <option key={item.chapter} value={item.chapter}>
                {item.chapter}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {[
            ["Theorems", selectedRevision.theorem, "emerald"],
            ["Formulas", selectedRevision.formula, "blue"],
            ["Important Tips", selectedRevision.tips, "amber"],
          ].map(([title, items, tone]) => (
            <div key={String(title)} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-600">{String(title)}</h3>
              <div className="mt-3 space-y-2">
                {(items as string[]).map((item) => (
                  <div key={item} className={`rounded-md bg-white px-3 py-2 text-sm leading-6 text-slate-800 shadow-sm border-l-4 ${
                    tone === "emerald" ? "border-emerald-400" : tone === "blue" ? "border-blue-400" : "border-amber-400"
                  }`}>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Weak Topics</h2>
          <div className="mt-4 space-y-3">
            {topics.length ? (
              topics.map(([topic, count]) => (
                <div key={topic} className="flex items-center justify-between rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-800">
                  <span>{topic}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak topics recorded yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">Weak Areas</h2>
          <div className="mt-4 space-y-3">
            {mistakes.length ? (
              mistakes.map(([type, count]) => (
                <div key={type} className="flex items-center justify-between rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  <span>{type.replace(/_/g, " ")}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak areas recorded yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
          <h2 className="font-semibold text-slate-950">JEE Patterns to Improve</h2>
          <div className="mt-4 space-y-3">
            {patterns.length ? (
              patterns.map(([pattern, count]) => (
                <div key={pattern} className="flex items-center justify-between rounded-xl bg-orange-50 px-3 py-2 text-sm text-orange-800">
                  <span>{pattern}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No weak JEE patterns recorded yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-md">
        <h2 className="font-semibold text-slate-950">📘 Concepts Learned</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {stats.conceptsLearned.length ? (
            stats.conceptsLearned.map((concept) => (
              <span key={concept} className="rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-800">
                {concept}
              </span>
            ))
          ) : (
            <p className="text-sm text-slate-500">Start a Tutor session to add concepts here.</p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-950">Recent performance</h2>
        <div className="mt-4 space-y-2">
          {stats.recent.map((response, index) => (
            <div key={index} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {response.correct ? "Correct" : "Incorrect"} {response.mistake_type ? `- ${response.mistake_type}` : ""}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
