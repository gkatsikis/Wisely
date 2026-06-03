"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export default function ProfilePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="container">
        <p>Loading…</p>
      </main>
    );
  }

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");

  return (
    <main className="container">
      <div className="card">
        <h1>Your profile</h1>
        <div className="stack">
          <div>
            <span className="muted">Username</span>
            <br />
            <strong>{user.username}</strong>
          </div>
          <div>
            <span className="muted">Email</span>
            <br />
            <strong>{user.email || "—"}</strong>
          </div>
          <div>
            <span className="muted">Name</span>
            <br />
            <strong>{fullName || "—"}</strong>
          </div>
        </div>
      </div>
    </main>
  );
}
