"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { GoogleButton } from "@/components/GoogleButton";

const GOOGLE_ENABLED = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="container">
      <div className="card">
        <h1>Log in</h1>
        <form onSubmit={onSubmit}>
          <label htmlFor="username">Username or email</label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Log in"}
          </button>
        </form>

        <div className="divider">or</div>
        {GOOGLE_ENABLED ? (
          <GoogleButton />
        ) : (
          <p className="hint">
            Google sign-in is off — set <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> to enable it.
          </p>
        )}

        <p className="muted" style={{ marginTop: "1rem" }}>
          No account? <Link href="/signup">Sign up</Link>
        </p>
      </div>
    </main>
  );
}
