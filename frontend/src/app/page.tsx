"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();

  return (
    <main className="container wide">
      <h1>Wisely</h1>
      <p className="muted">
        Book reviews from licensed clinicians — a demo frontend wired to the Django API.
      </p>

      <div className="card" style={{ marginTop: "1.5rem" }}>
        {loading ? (
          <p>Loading…</p>
        ) : user ? (
          <>
            <p>
              You are signed in as <strong>{user.username}</strong>.
            </p>
            <p>
              <Link href="/profile">View your profile →</Link>
            </p>
          </>
        ) : (
          <div className="stack">
            <p>You are not signed in.</p>
            <p>
              <Link href="/login">Log in</Link>
            </p>
            <p>
              <Link href="/signup">Create an account</Link>
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
