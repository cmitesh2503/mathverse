"use client";

import { useState } from "react";
import { TopNav } from "./components/TopNav";
import Classroom from "./pages/Classroom";
import Exam from "./pages/Exam";
import Home from "./pages/Home";
import Homework from "./pages/Homework";
import Learn from "./pages/Learn";
import Practice from "./pages/Practice";
import Progress from "./pages/Progress";
import Solve from "./pages/Solve";
import TutorSession from "./pages/TutorSession";

export type PageKey = "home" | "class" | "learn" | "tutor" | "practice" | "homework" | "solve" | "exam" | "progress";

export default function App() {
  const [page, setPage] = useState<PageKey>("home");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <TopNav active={page} onNavigate={setPage} />
      {page === "home" && <Home onNavigate={setPage} />}
      {page === "class" && <Classroom onNavigate={setPage} />}
      {page === "learn" && <Learn onNavigate={setPage} />}
      {page === "tutor" && <TutorSession onNavigate={setPage} />}
      {page === "practice" && <Practice />}
      {page === "homework" && <Homework onNavigate={setPage} />}
      {page === "solve" && <Solve onNavigate={setPage} />}
      {page === "exam" && <Exam />}
      {page === "progress" && <Progress />}
    </div>
  );
}
