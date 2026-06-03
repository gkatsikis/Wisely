# Wisely — Frontend

Next.js (App Router) client for the Wisely API. Authenticates against the Django backend with JWTs.

## Setup

```bash
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL defaults to http://localhost:8000
npm run dev                   # http://localhost:3000
```

The backend must be running (see [../backend/README.md](../backend/README.md)); its CORS config already allows `http://localhost:3000`.

## Auth

- **Username/password** at `/login` and `/signup`. Registration requires an email; the backend sends a **mandatory** verification link (printed to the backend console in dev) — confirm it before logging in.
- JWT **access + refresh** tokens are kept in `localStorage` and sent as `Authorization: Bearer`. The access token is auto-refreshed on load when expired.
- **Google**: set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (and the backend's `GOOGLE_OAUTH_*`) to enable the "Continue with Google" button.

> Note: `localStorage` token storage is simple but exposed to XSS; for production, consider httpOnly cookies.

## Structure

- `src/lib/api.ts` — typed fetch client (base URL + bearer token).
- `src/lib/auth.tsx` — `AuthProvider` / `useAuth` (login, register, logout, refresh).
- `src/components/` — `Providers`, `NavBar`, `GoogleButton`.
- `src/app/` — `page` (home), `login`, `signup`, `profile` (protected).
