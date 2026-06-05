"use client";

import { useEffect, useState } from "react";
import type { PageKey } from "../App";
import CheckoutPanel from "../components/CheckoutPanel";
import SignupForm from "../components/SignupForm";

type SignupState = {
  userId: string;
  grade: string;
};

type Props = {
  onNavigate: (page: PageKey) => void;
};

export default function Subscription({ onNavigate }: Props) {
  const [signup, setSignup] = useState<SignupState | null>(null);
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("mathverse_user_id");
    const grade = localStorage.getItem("mathverse_grade");
    if (userId && grade) {
      setSignup({ userId, grade });
    }
  }, []);

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-slate-50 px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase text-blue-700">Subscription</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Sign up to start learning</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Chapter 1 is free for every grade. Subscribe when you are ready to continue into the remaining chapters.
          </p>
        </div>

        {!signup ? (
          <SignupForm onSignupSuccess={(userId: string, grade: string) => setSignup({ userId, grade })} />
        ) : unlocked ? (
          <div className="rounded-lg border border-emerald-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase text-emerald-700">Subscription active</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Grade {signup.grade} access is unlocked.</h2>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase text-blue-700">Step 2</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">Free Chapter 1 is unlocked</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Start with the first chapter now. The app will ask for subscription when you choose Chapter 2 or later.
              </p>
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-slate-500">Student ID</dt>
                  <dd className="mt-1 break-all text-slate-900">{signup.userId}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-500">Grade</dt>
                  <dd className="mt-1 text-slate-900">{signup.grade}</dd>
                </div>
              </dl>
              <button
                type="button"
                onClick={() => onNavigate("class")}
                className="mt-6 rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
              >
                Start free Chapter 1
              </button>
            </div>
            <CheckoutPanel userId={signup.userId} grade={signup.grade} onSubscriptionUnlocked={() => setUnlocked(true)} />
          </div>
        )}
      </div>
    </main>
  );
}
