# Wisely API

Django + DRF backend. **Run all commands below from this `backend/` directory.** For what the project is and how it's designed, see [../docs/DESIGN.md](../docs/DESIGN.md).

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python is managed by uv; the project targets 3.13)
- PostgreSQL (local), **or** Docker + Docker Compose

## Setup — local (uv)

```bash
# 1. Install dependencies (creates .venv with the right Python)
uv sync

# 2. Configure environment
cp .env.example .env        # then edit values as needed

# 3. Create the database role + database (defaults match .env)
psql -d postgres -c "CREATE ROLE wisely WITH LOGIN PASSWORD 'wisely' CREATEDB;"
psql -d postgres -c "CREATE DATABASE wisely OWNER wisely;"

# 4. Migrate and create an admin user
uv run python wisely_api/manage.py migrate
uv run python wisely_api/manage.py createsuperuser
```

## Docker

The full stack (database + backend + **frontend**) is orchestrated from the **repo root** — see the [root README](../README.md):

```bash
cd ..                       # repo root
docker compose up --build   # db + backend (:8000) + frontend (:3000)
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

The DB container publishes on host port **5433** (to avoid clashing with a local Postgres on 5432); the backend reaches it internally as `db:5432`.

## Running

```bash
# local
uv run python wisely_api/manage.py runserver
# (Docker runs the server automatically — see the root README)
```

App: http://localhost:8000/ · Admin: http://localhost:8000/admin/

## Management commands

```bash
# Import a book from Google Books (Open Library cover fallback) into the catalog
uv run python wisely_api/manage.py import_book "the body keeps the score"
uv run python wisely_api/manage.py import_book "isbn:9780143127741"
uv run python wisely_api/manage.py import_book "trauma" --limit 5
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/registration/` | sign up (username, email, password1/2) → JWT |
| POST | `/api/auth/login/` | log in (username or email + password) → JWT access + refresh |
| POST | `/api/auth/logout/` | log out (blacklists the refresh token) |
| GET/PUT | `/api/auth/user/` | current user |
| POST | `/api/auth/token/refresh/` | refresh the access token |
| POST | `/api/auth/google/` | exchange a Google token/code → JWT |
| GET | `/api/health/` | health check |
| GET | `/api/books/` | list the catalog |
| GET | `/api/books/{id}/` | book detail (audience vs critic scores, reviews, buy links) |
| GET | `/api/books/search/?q=` | live Google Books search (not persisted) |
| POST | `/api/books/import/` | import a volume (`volume_id`, `isbn`, or `query`) |
| GET | `/api/books/{id}/buy/?provider=bookshop\|amazon` | log affiliate click + redirect to retailer |
| — | `/api/clinicians/`, `/api/seekers/` | reserved (no endpoints yet) |

## Environment variables

Set in `.env` (see `.env.example`). Docker Compose reads it for interpolation; locally it's loaded by `python-dotenv`.

| Variable | Default | Notes |
|----------|---------|-------|
| `DEBUG` | `True` | |
| `SECRET_KEY` | dev key | set a real one in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `wisely` | |
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | Compose sets `DB_HOST=db` |
| `GOOGLE_BOOKS_API_KEY` | _(empty)_ | optional; raises Google Books rate limits |
| `BOOK_COVER_POLICY` | `auto` | `auto` or `openlibrary_only` |
| `BOOKSHOP_AFFILIATE_ID` / `AMAZON_ASSOCIATE_TAG` | _(empty)_ | for affiliate buy-links |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_SECRET` | _(empty)_ | Google social login |
| `GOOGLE_OAUTH_CALLBACK_URL` | `http://localhost:3000/...` | where the frontend handles the Google redirect |
