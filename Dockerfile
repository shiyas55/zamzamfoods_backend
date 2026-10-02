# ────────────────────────────────────────────────────────────────────────────
# Zamzam Foods — Production Dockerfile
# Backend: Django 4.2 + Gunicorn
# Deployment: Koyeb (Docker via GitHub)
# ────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Django must use production settings in this container
ENV DJANGO_ENV=production

WORKDIR /app

# ── Install system dependencies ───────────────────────────────────────────────
# libpq-dev is required for psycopg2 compilation, postgresql-client provides pg_dump
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*


# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────────────────────────
COPY . .

# ── Collect static files (WhiteNoise serves them) ────────────────────────────
# DATABASE_URL is not needed for collectstatic but DJANGO_SECRET_KEY must be set.
# Koyeb injects these at build time OR you can use --env-file.
# We use a dummy secret here solely for collectstatic — the real one is injected at runtime.
RUN DJANGO_SECRET_KEY="collectstatic-dummy-key-not-used-at-runtime" \
    DJANGO_ALLOWED_HOSTS="localhost" \
    DATABASE_URL="postgresql://placeholder:placeholder@localhost:5432/placeholder" \
    python manage.py collectstatic --noinput

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Entrypoint: migrate then start Gunicorn ───────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
