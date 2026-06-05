import React, { useMemo, useState } from "react";
import { createFirestoreCredentials, saveSession } from "../services/firestoreAuth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const requestTimeoutMs = 15000;

function createStudentId() {
  if (crypto?.randomUUID) {
    return `student_${crypto.randomUUID()}`;
  }
  return `student_${Date.now()}`;
}

export default function SignupForm({ onSignupSuccess }) {
  const generatedUid = useMemo(() => createStudentId(), []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [credentials, setCredentials] = useState({
    password: "",
    confirmPassword: "",
  });
  const [formData, setFormData] = useState({
    uid: generatedUid,
    personal_details: {
      full_name: "",
      email: "",
      mobile_no: "",
      address: { street: "", city: "", state: "", pincode: "", country: "India" },
    },
    parent_details: { parent_name: "", parent_mobile: "", parent_email: "" },
    academic_profile: {
      current_grade: "10",
      school_board: "CBSE",
      school_name: "",
      default_teaching_language: "en-IN",
    },
  });

  const updatePersonal = (field, value) => {
    setFormData((current) => ({
      ...current,
      personal_details: { ...current.personal_details, [field]: value },
    }));
  };

  const updateAddress = (field, value) => {
    setFormData((current) => ({
      ...current,
      personal_details: {
        ...current.personal_details,
        address: { ...current.personal_details.address, [field]: value },
      },
    }));
  };

  const updateParent = (field, value) => {
    setFormData((current) => ({
      ...current,
      parent_details: { ...current.parent_details, [field]: value },
    }));
  };

  const updateAcademic = (field, value) => {
    setFormData((current) => ({
      ...current,
      academic_profile: { ...current.academic_profile, [field]: value },
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (credentials.password.length < 8) {
      alert("Password must be at least 8 characters.");
      return;
    }
    if (credentials.password !== credentials.confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
        signal: controller.signal,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Signup failed.");
      }

      await createFirestoreCredentials(
        formData.uid,
        formData.personal_details.email,
        credentials.password,
      );

      const session = {
        uid: formData.uid,
        email: formData.personal_details.email,
        grade: formData.academic_profile.current_grade,
        fullName: formData.personal_details.full_name,
        authMethod: "firestore",
      };
      saveSession(session);
      onSignupSuccess?.(formData.uid, formData.academic_profile.current_grade, session);
    } catch (error) {
      const message = error?.name === "AbortError" ? "Signup timed out. Check that the backend is ready and Firestore credentials are configured." : error instanceof Error ? error.message : "Signup failed.";
      alert(message);
    } finally {
      window.clearTimeout(timeoutId);
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-blue-700">Step 1</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Create student profile</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <input required type="text" placeholder="Student full name" className="rounded border border-slate-300 p-3" onChange={(event) => updatePersonal("full_name", event.target.value)} />
        <input required type="email" placeholder="Student email" className="rounded border border-slate-300 p-3" onChange={(event) => updatePersonal("email", event.target.value)} />
        <input required type="tel" placeholder="Student mobile, e.g. +919876543210" className="rounded border border-slate-300 p-3" onChange={(event) => updatePersonal("mobile_no", event.target.value)} />
        <input required type="text" placeholder="School name" className="rounded border border-slate-300 p-3" onChange={(event) => updateAcademic("school_name", event.target.value)} />
        <input
          required
          type="password"
          minLength={8}
          placeholder="Create password"
          className="rounded border border-slate-300 p-3"
          value={credentials.password}
          onChange={(event) => setCredentials((current) => ({ ...current, password: event.target.value }))}
        />
        <input
          required
          type="password"
          minLength={8}
          placeholder="Confirm password"
          className="rounded border border-slate-300 p-3"
          value={credentials.confirmPassword}
          onChange={(event) => setCredentials((current) => ({ ...current, confirmPassword: event.target.value }))}
        />
      </div>

      <h3 className="mt-6 text-sm font-semibold uppercase text-slate-500">Address</h3>
      <div className="mt-3 grid gap-4 md:grid-cols-4">
        <input required type="text" placeholder="Street address" className="rounded border border-slate-300 p-3 md:col-span-4" onChange={(event) => updateAddress("street", event.target.value)} />
        <input required type="text" placeholder="City" className="rounded border border-slate-300 p-3" onChange={(event) => updateAddress("city", event.target.value)} />
        <input required type="text" placeholder="State" className="rounded border border-slate-300 p-3" onChange={(event) => updateAddress("state", event.target.value)} />
        <input required type="text" placeholder="Pincode" className="rounded border border-slate-300 p-3" onChange={(event) => updateAddress("pincode", event.target.value)} />
        <input required type="text" placeholder="Country" value={formData.personal_details.address.country} className="rounded border border-slate-300 p-3" onChange={(event) => updateAddress("country", event.target.value)} />
      </div>

      <h3 className="mt-6 text-sm font-semibold uppercase text-slate-500">Parent details</h3>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        <input required type="text" placeholder="Parent name" className="rounded border border-slate-300 p-3" onChange={(event) => updateParent("parent_name", event.target.value)} />
        <input required type="tel" placeholder="Parent mobile" className="rounded border border-slate-300 p-3" onChange={(event) => updateParent("parent_mobile", event.target.value)} />
        <input type="email" placeholder="Parent email optional" className="rounded border border-slate-300 p-3" onChange={(event) => updateParent("parent_email", event.target.value || null)} />
      </div>

      <h3 className="mt-6 text-sm font-semibold uppercase text-slate-500">Academic settings</h3>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        <select value={formData.academic_profile.current_grade} className="rounded border border-slate-300 p-3" onChange={(event) => updateAcademic("current_grade", event.target.value)}>
          <option value="10">Grade 10</option>
          <option value="11">Grade 11</option>
          <option value="12">Grade 12</option>
        </select>
        <select value={formData.academic_profile.school_board} className="rounded border border-slate-300 p-3" onChange={(event) => updateAcademic("school_board", event.target.value)}>
          <option value="CBSE">CBSE</option>
          <option value="ICSE">ICSE</option>
          <option value="State Board">State Board</option>
        </select>
        <select value={formData.academic_profile.default_teaching_language} className="rounded border border-slate-300 p-3" onChange={(event) => updateAcademic("default_teaching_language", event.target.value)}>
          <option value="en-IN">English</option>
          <option value="hi-IN">Hindi</option>
        </select>
      </div>

      <button type="submit" disabled={isSubmitting} className="mt-6 w-full rounded bg-blue-700 p-3 font-semibold text-white hover:bg-blue-800 disabled:bg-slate-400">
        {isSubmitting ? "Creating login..." : "Create login and continue"}
      </button>
    </form>
  );
}
