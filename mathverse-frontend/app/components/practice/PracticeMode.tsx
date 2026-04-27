"use client";

import { useState } from "react";

type PracticeResult = {
  correct: boolean;
  mistake_type?: string | null;
  hint?: string | null;
  explanation?: string | null;
  steps?: string;
};

type PracticeModeProps = {
  question: string;
  onSubmitAnswer: (answer: string) => Promise<PracticeResult>;
  onNext?: () => void;
};

export default function PracticeMode({
  question,
  onSubmitAnswer,
  onNext,
}: PracticeModeProps) {

  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);

  // ✅ SUBMIT
  const handleSubmit = async () => {
    if (!answer.trim() || loading) return;

    setLoading(true);

    try {
      const res = await onSubmitAnswer(answer.trim());
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // ✅ NEXT
  const handleNext = () => {
    setAnswer("");
    setResult(null);
    setExplanation(null);
    onNext?.();
  };

  // ✅ EXPLAIN
  const handleExplain = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/practice/explain", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: "math-session-1",
          answer,
        }),
      });

      const data = await res.json();
      setExplanation(data.explanation);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-4">

      {/* QUESTION */}
      <div className="bg-white p-4 rounded shadow">
        <p>{question}</p>
      </div>

      {/* INPUT */}
      <div className="mt-4 flex gap-2">
        <input
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          className="border p-2 flex-1"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-600 text-white px-4"
        >
          {loading ? "Submitting..." : "Submit"}
        </button>
      </div>

      {/* RESULT */}
      {result && (
        <div className="mt-4 p-4 border rounded">

          {result.correct ? (
            <p className="text-green-600">✅ {result.explanation}</p>
          ) : (
            <>
              <p className="text-red-600">❌ Incorrect</p>

              {result.mistake_type && <p>🧠 {result.mistake_type}</p>}
              {result.hint && <p>💡 {result.hint}</p>}
              {result.explanation && <p>{result.explanation}</p>}
            </>
          )}

          {!result.correct && (
            <button onClick={handleExplain}>
              Explain
            </button>
          )}

          {/* STEP SOLUTION */}
          {result.steps && (
            <div className="mt-2 bg-gray-100 p-2">
              📘 {result.steps}
            </div>
          )}

          {/* BUTTONS */}
          <div className="mt-3 flex gap-2">
            <button onClick={handleNext} className="bg-black text-white px-3">
              Next
            </button>

            <button onClick={handleExplain} className="bg-blue-500 text-white px-3">
              Explain
            </button>
          </div>

          {/* EXTRA EXPLANATION */}
          {explanation && (
            <div className="mt-2 bg-blue-100 p-2">
              {explanation}
            </div>
          )}

        </div>
      )}

    </div>
  );
}