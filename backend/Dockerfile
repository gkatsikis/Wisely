FROM python:3.13-slim

# uv: fast Python package/dependency manager (replaces pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Keep the project venv outside /code so the docker-compose bind mount can't shadow it,
# and put it on PATH so `python`/`django-admin` resolve to it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /code

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the application code
COPY . .
