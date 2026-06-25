import { useState } from "react";

import { TopNav } from "./components/TopNav";
import SignupForm from "./components/SignupForm";

import {
  clearStoredSession,
  loadStoredSession,
  type MathverseSession
} from "./services/firestoreAuth";

import Classroom from "./pages/Classroom";
import Exam from "./pages/Exam";
import ForgotPassword from "./pages/ForgotPassword";
import Home from "./pages/Home";
import Homework from "./pages/Homework";
import Learn from "./pages/Learn";
import Login from "./pages/Login";
import Practice from "./pages/Practice";
import Progress from "./pages/Progress";
import Solve from "./pages/Solve";
import StudentReport from "./pages/StudentReport";
import Subscription from "./pages/Subscription";
import TutorSession from "./pages/TutorSession";

import JeeHome from "./pages/jee/JeeHome";
import JeeVoiceTutor from "./pages/JeeVoiceTutor";
import JeeSolveQuestion from "./pages/jee/JeeSolveQuestion";

export type PageKey =
  | "home"
  | "jee-home"
  | "jee-solve"
  | "voice-tutor"
  | "class"
  | "learn"
  | "tutor"
  | "practice"
  | "homework"
  | "solve"
  | "exam"
  | "progress"
  | "report"
  | "subscription";

type AuthView =
  | "login"
  | "signup"
  | "reset";

export default function App() {

  const [session, setSession] =
    useState<MathverseSession | null>(
      () => loadStoredSession()
    );

  const [authView, setAuthView] =
    useState<AuthView>("login");

  const [page, setPage] =
    useState<PageKey>("jee-home");

  if (!session) {

    if (authView === "signup") {

      return (
        <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6">

          <div className="mx-auto max-w-5xl">

            <div className="mb-6 flex items-center justify-between gap-4">

              <div>
                <p className="text-sm font-semibold uppercase text-blue-700">
                  MathVerse
                </p>

                <h1 className="mt-2 text-3xl font-semibold text-slate-950">
                  Create your login
                </h1>
              </div>

              <button
                type="button"
                onClick={() =>
                  setAuthView("login")
                }
                className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Back to Login
              </button>

            </div>

            <SignupForm
              onSignupSuccess={(
                _userId,
                _grade,
                createdSession
              ) => {

                setSession(
                  createdSession ??
                  loadStoredSession()
                );

                setPage(
                  "subscription"
                );
              }}
            />

          </div>

        </main>
      );
    }

    if (authView === "reset") {

      return (
        <ForgotPassword
          onBackToLogin={() =>
            setAuthView("login")
          }
        />
      );
    }

    return (
      <Login
        onLoginSuccess={(
          nextSession
        ) => {

          setSession(
            nextSession
          );

          setPage(
            "jee-home"
          );
        }}
        onCreateAccount={() =>
          setAuthView("signup")
        }
        onForgotPassword={() =>
          setAuthView("reset")
        }
      />
    );
  }

  const handleLogout = () => {

    clearStoredSession();

    setSession(null);

    setAuthView("login");

    setPage("jee-home");
  };

  return (

    <div className="min-h-screen bg-slate-50 text-slate-950">

      <TopNav
        active={page}
        onNavigate={setPage}
        session={session}
        onLogout={handleLogout}
      />

      {/* JEE */}

      {page === "jee-home" && (
        <JeeHome
          onNavigate={setPage}
        />
      )}

      {
        page === "jee-solve" &&(
         <JeeSolveQuestion 
            onNavigate={setPage}
          />
          )}

      {page === "voice-tutor" && (
        <JeeVoiceTutor />
      )}

      {/* CBSE */}

      {page === "home" && (
        <Home
          onNavigate={setPage}
        />
      )}

      {page === "class" && (
        <Classroom
          onNavigate={setPage}
        />
      )}

      {page === "learn" && (
        <Learn
          onNavigate={setPage}
        />
      )}

      {page === "tutor" && (
        <TutorSession
          onNavigate={setPage}
        />
      )}

      {page === "practice" && (
        <Practice />
      )}

      {page === "homework" && (
        <Homework
          onNavigate={setPage}
        />
      )}

      {page === "solve" && (
        <Solve
          onNavigate={setPage}
        />
      )}

      {page === "exam" && (
        <Exam />
      )}

      {page === "progress" && (
        <Progress />
      )}

      {page === "report" && (
        <StudentReport
          onNavigate={setPage}
        />
      )}

      {page === "subscription" && (
        <Subscription
          onNavigate={setPage}
        />
      )}

    </div>
  );
}