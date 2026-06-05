import React, { useState } from "react";
import { loginWithFirestore, type MathverseSession } from "../services/firestoreAuth";

type Props = {
  onLoginSuccess: (session: MathverseSession) => void;
  onCreateAccount: () => void;
  onForgotPassword: () => void;
};

export const Login: React.FC<Props> = ({ onLoginSuccess, onCreateAccount, onForgotPassword }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const session = await loginWithFirestore(email.trim(), password);
      onLoginSuccess(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-center text-3xl font-semibold text-slate-950">Mathverse</h1>
        <p className="mt-2 text-center text-sm text-slate-600">Sign in to continue learning</p>

        {error && (
          <div className="mt-5 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="student@example.com"
              required
              className="w-full rounded border border-slate-300 px-4 py-2 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              required
              className="w-full rounded border border-slate-300 px-4 py-2 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-blue-700 px-4 py-2 font-semibold text-white transition hover:bg-blue-800 disabled:bg-slate-400"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-200 pt-6 text-center">
          <button
            type="button"
            onClick={onForgotPassword}
            className="text-sm font-semibold text-blue-700 hover:underline"
          >
            Reset password
          </button>
          <p className="mt-4 text-sm text-slate-600">
            Need an account?{" "}
            <button type="button" onClick={onCreateAccount} className="font-semibold text-blue-700 hover:underline">
              Create one
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
