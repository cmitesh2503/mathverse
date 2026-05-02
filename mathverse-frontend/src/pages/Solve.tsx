"use client";

import { useState } from "react";
import { sendAnswer, type TutorResponse } from "../services/api";
import { ResponsePanel } from "../components/ResponsePanel";
import { useTutorStore } from "../store/useTutorStore";
import type { PageKey } from "../App";

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function Solve({ onNavigate }: Props) {
  const sessionId = useTutorStore((state) => state.session_id);
  const examMode = useTutorStore((state) => state.exam_mode);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<TutorResponse | null>(null);

  async function solve() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const data = await sendAnswer({
        session_id: sessionId,
        mode: "doubt",
        input: { question },
        context: { exam: examMode },
      });
      setResponse(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-950">Solve</h1>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">Image upload placeholder</div>
          <div className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">Voice input placeholder</div>
        </div>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Type a question..."
          className="mt-5 min-h-40 w-full rounded-md border border-slate-300 p-3 outline-none focus:ring-2 focus:ring-slate-900"
        />
        <div className="mt-4 flex gap-3">
          <button onClick={solve} disabled={loading} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300">
            {loading ? "Solving..." : "Solve"}
          </button>
          <button onClick={() => onNavigate("practice")} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">
            Start Practice
          </button>
        </div>
      </section>
      <ResponsePanel response={response} />
    </main>
  );
}
