"use client";

import { type ReactNode } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";

import { AuthProvider } from "@/lib/auth";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export function Providers({ children }: { children: ReactNode }) {
  const tree = <AuthProvider>{children}</AuthProvider>;
  // Only wrap in the Google provider when a client ID is configured.
  return GOOGLE_CLIENT_ID ? (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>{tree}</GoogleOAuthProvider>
  ) : (
    tree
  );
}
