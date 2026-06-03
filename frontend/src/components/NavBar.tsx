"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

export function NavBar() {
  const { user, loading, logout } = useAuth();

  return (
    <nav className="nav">
      <Link href="/" className="brand">
        Wisely
      </Link>
      <div className="nav-links">
        {loading ? null : user ? (
          <>
            <Link href="/profile">{user.username}</Link>
            <button type="button" className="link-button" onClick={() => logout()}>
              Log out
            </button>
          </>
        ) : (
          <>
            <Link href="/login">Log in</Link>
            <Link href="/signup">Sign up</Link>
          </>
        )}
      </div>
    </nav>
  );
}
