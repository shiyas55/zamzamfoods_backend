"""
Development settings for Zamzam Foods.
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
ALLOWED_HOSTS += ["localhost", "127.0.0.1", "0.0.0.0", ".ts.net", "shiyass-macbook-air.tail4ef336.ts.net", "testserver"]

# SQLite for local development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
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
