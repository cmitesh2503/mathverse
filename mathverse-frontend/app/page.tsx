"use client";

import { useState } from "react";
import Chat from "@/app/components/Chat";
import TeacherAvatar from "@/app/components/TeacherAvatar";
import ClassWhiteboard from "@/app/components/ClassWhiteboard";
import PracticeMode from "@/app/components/practice/PracticeMode";
import { submitAnswer, getNextQuestion } from "@/app/lib/api/practice";

export default function Page() {
  const [mode, setMode] = useState<"learn" | "practice">("learn");
  const [question, setQuestion] = useState("Solve: x² - 5x + 6 = 0");

  return (
    <div className="h-screen w-screen flex flex-col bg-[#f5f5f5]">

      {/* 🔥 TOP NAV */}
      <div className="h-[60px] bg-white border-b flex items-center px-6 gap-6 z-10">
        <button
          onClick={() => setMode("learn")}
          className={`text-sm font-medium ${
            mode === "learn"
              ? "text-black border-b-2 border-black pb-1"
              : "text-gray-400"
          }`}
        >
          Learn
        </button>

        <button
          onClick={() => setMode("practice")}
          className={`text-sm font-medium ${
            mode === "practice"
              ? "text-black border-b-2 border-black pb-1"
              : "text-gray-400"
          }`}
        >
          Practice
        </button>
      </div>

      {/* 🔥 MAIN LAYOUT */}
      <div className="flex flex-1 overflow-hidden">

        {/* ✅ LEFT PANEL */}
        <div className="w-[260px] min-w-[260px] bg-white border-r overflow-y-auto p-4">
          <TeacherAvatar />
        </div>

        {/* ✅ CENTER PANEL */}
        <div className="flex-1 bg-gray-50 overflow-y-auto overflow-x-hidden p-4">

          {mode === "learn" && (
            <div className="h-full">
              <ClassWhiteboard />
            </div>
          )}

          {mode === "practice" && (
            <div className="max-w-[900px] mx-auto">
              <PracticeMode
                question={question}

                onSubmitAnswer={async (answer: string) => {
                  return await submitAnswer(answer);
                }}

                onNext={async () => {
                  console.log("CALLING NEXT API");

                  const res = await getNextQuestion();

                  console.log("NEXT RESPONSE:", res);

                  setQuestion(res.question);
                }}
              />
            </div>
          )}

        </div>

        {/* ✅ RIGHT PANEL */}
        <div className="w-[320px] min-w-[320px] bg-white border-l overflow-y-auto p-4">
          <p className="text-sm text-gray-500">
            Chat panel (we will fix this next)
          </p>
        </div>

      </div>
    </div>
  );
}