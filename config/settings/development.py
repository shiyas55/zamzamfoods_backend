"""
Development settings for Zamzam Foods.
Uses Supabase PostgreSQL (same as production) — no SQLite.
"""

import os
import dj_database_url
from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
ALLOWED_HOSTS += ["localhost", "127.0.0.1", "0.0.0.0", ".ts.net", "shiyass-macbook-air.tail4ef336.ts.net", "testserver"]

# ─── Database ─────────────────────────────────────────────────────────────────
# If DATABASE_URL is set and valid → Supabase/PostgreSQL
# If missing or still a placeholder  → fall back to local SQLite (dev only)
DATABASE_URL_ENV = os.environ.get("DATABASE_URL", "").strip()

_use_sqlite_fallback = not DATABASE_URL_ENV or any(
    p in DATABASE_URL_ENV for p in ["[YOUR-PASSWORD]", "<your-", "<password>", "YOUR_PASSWORD"]
)

if _use_sqlite_fallback:
    import warnings
    warnings.warn(
        "\n\n⚠️  DATABASE_URL not configured — using local SQLite (db.sqlite3).\n"
        "    To connect to Supabase PostgreSQL, update DATABASE_URL in backend/.env\n"
        "    with your Supabase Session Pooler URI from:\n"
        "    https://supabase.com/dashboard/project/mfrakyarmmnvsvzlyota/settings/database\n",
        UserWarning,
        stacklevel=2,
    )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    _is_internal = any(h in DATABASE_URL_ENV for h in ["railway.internal", "localhost", "127.0.0.1"])
    _ssl_require = not _is_internal
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL_ENV,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=_ssl_require,
        )
    }

# CORS settings for development (React dev server on port 5173 & Tailscale)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS += [
    "https://shiyass-macbook-air.tail4ef336.ts.net",
    "http://shiyass-macbook-air.tail4ef336.ts.net",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS += [
    "https://shiyass-macbook-air.tail4ef336.ts.net",
    "http://shiyass-macbook-air.tail4ef336.ts.net",
]

# Development logging
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["root"]["level"] = "DEBUG"
