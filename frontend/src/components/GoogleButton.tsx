"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useGoogleLogin } from "@react-oauth/google";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Renders only when NEXT_PUBLIC_GOOGLE_CLIENT_ID is set (see Providers / login page),
// so useGoogleLogin always runs inside a GoogleOAuthProvider.
export function GoogleButton() {
  const { loginWithTokens } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await api.post<{ access: string; refresh: string }>(
          "/api/auth/google/",
          { access_token: tokenResponse.access_token },
          false,
        );
        await loginWithTokens(res.access, res.refresh);
        router.push("/");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Google sign-in failed");
      }
    },
    onError: () => setError("Google sign-in failed"),
  });

  return (
    <>
      <button type="button" className="btn btn-secondary" onClick={() => googleLogin()}>
        Continue with Google
      </button>
      {error && <p className="error">{error}</p>}
    </>
  );
}
