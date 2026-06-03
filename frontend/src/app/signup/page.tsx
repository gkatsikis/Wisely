"use client";

import { useState } from "react";
import Link from "next/link";

import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function SignupPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({ username: "", email: "", password1: "", password2: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(form);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign up failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <main className="container">
        <div className="card">
          <h1>Check your email</h1>
          <p className="muted">
            We sent a verification link to <strong>{form.email}</strong>. Confirm your address,
            then <Link href="/login">log in</Link>.
          </p>
          <p className="hint">In local dev the email is printed to the backend server console.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="container">
      <div className="card">
        <h1>Create your account</h1>
        <form onSubmit={onSubmit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={form.username}
            onChange={update("username")}
            autoComplete="username"
            required
          />
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={form.email}
            onChange={update("email")}
            autoComplete="email"
            required
          />
          <label htmlFor="password1">Password</label>
          <input
            id="password1"
            type="password"
            value={form.password1}
            onChange={update("password1")}
            autoComplete="new-password"
            required
          />
          <label htmlFor="password2">Confirm password</label>
          <input
            id="password2"
            type="password"
            value={form.password2}
            onChange={update("password2")}
            autoComplete="new-password"
            required
          />
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Sign up"}
          </button>
        </form>

        <p className="muted" style={{ marginTop: "1rem" }}>
          Already have an account? <Link href="/login">Log in</Link>
        </p>
      </div>
    </main>
  );
}
