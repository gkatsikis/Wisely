# Wisely

Monorepo for Wisely. See **[docs/DESIGN.md](docs/DESIGN.md)** for what the project is and how it's designed.

## Layout

- **[backend/](backend/)** — Django + DRF API. Local setup: [backend/README.md](backend/README.md).
- **[frontend/](frontend/)** — Next.js (App Router) web app. Local setup: [frontend/README.md](frontend/README.md).

## Run the whole stack with Docker

From the repo root:

```bash
docker compose up --build           # db + backend (:8000) + frontend (:3000)

# first run only — set up the database (in another terminal):
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

- Frontend → http://localhost:3000 · Backend API → http://localhost:8000 · Admin → http://localhost:8000/admin/
- Postgres publishes on host port **5433** (avoids clashing with a local Postgres on 5432); inside the network the backend reaches it as `db:5432`.
- Source is bind-mounted, so code edits hot-reload without a rebuild. The backend reads secrets from `backend/.env`; the frontend reads `NEXT_PUBLIC_*` from `frontend/.env.local`.

## Run locally without Docker

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).
