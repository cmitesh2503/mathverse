export type MathverseSession = {
  uid: string;
  email: string;
  grade?: string;
  fullName?: string;
  authMethod?: string;
};

type LoginResponse = {
  uid: string;
  email: string;
  grade?: string | number | null;
  full_name?: string | null;
  auth_method?: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const authBaseUrl = `${apiBaseUrl}/api/auth/firestore`;

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Request failed.";
    throw new Error(detail);
  }

  return data as T;
}

function normalizeGrade(grade: string | number | null | undefined): string | undefined {
  if (grade === null || grade === undefined || grade === "") {
    return undefined;
  }
  return String(grade);
}

export function saveSession(session: MathverseSession) {
  localStorage.setItem("mathverse_user_id", session.uid);
  localStorage.setItem("mathverse_auth_email", session.email);

  if (session.grade) {
    localStorage.setItem("mathverse_grade", session.grade);
  }

  if (session.fullName) {
    localStorage.setItem("mathverse_full_name", session.fullName);
  }
}

export function loadStoredSession(): MathverseSession | null {
  const uid = localStorage.getItem("mathverse_user_id");
  const email = localStorage.getItem("mathverse_auth_email");

  if (!uid || !email) {
    return null;
  }

  return {
    uid,
    email,
    grade: localStorage.getItem("mathverse_grade") || undefined,
    fullName: localStorage.getItem("mathverse_full_name") || undefined,
    authMethod: "firestore",
  };
}

export function clearStoredSession() {
  localStorage.removeItem("mathverse_user_id");
  localStorage.removeItem("mathverse_auth_email");
  localStorage.removeItem("mathverse_grade");
  localStorage.removeItem("mathverse_full_name");
}

export async function loginWithFirestore(email: string, password: string): Promise<MathverseSession> {
  const data = await parseJsonResponse<LoginResponse>(
    await fetch(`${authBaseUrl}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
  );

  const session: MathverseSession = {
    uid: data.uid,
    email: data.email,
    grade: normalizeGrade(data.grade),
    fullName: data.full_name || undefined,
    authMethod: data.auth_method || "firestore",
  };

  saveSession(session);
  return session;
}

export async function createFirestoreCredentials(uid: string, email: string, password: string) {
  await parseJsonResponse(
    await fetch(`${authBaseUrl}/create-credentials`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid, email, password }),
    }),
  );
}

export async function requestPasswordResetToken(email: string): Promise<string> {
  const data = await parseJsonResponse<{ reset_token?: string }>(
    await fetch(`${authBaseUrl}/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }),
  );

  if (!data.reset_token) {
    throw new Error("Password reset token was not returned.");
  }

  return data.reset_token;
}

export async function resetFirestorePassword(token: string, newPassword: string) {
  await parseJsonResponse(
    await fetch(`${authBaseUrl}/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    }),
  );
}
