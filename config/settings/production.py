"""
Production settings for Zamzam Foods.
Enforces strict security, HTTPS headers, WhiteNoise static files,
and PostgreSQL via DATABASE_URL environment variable.
"""

import os
import dj_database_url
from .base import *

# ─── Core ─────────────────────────────────────────────────────────────────────
DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
_default_hosts = [
    "zamzamfood.up.railway.app",
    "zamzamfoods.up.railway.app",
    "localhost",
    "127.0.0.1",
]
for h in _default_hosts:
    if h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(h)

# ─── Database ─────────────────────────────────────────────────────────────────
# Supabase PostgreSQL via DATABASE_URL
# Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE
DATABASE_URL_ENV = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL_ENV:
    raise ValueError("DATABASE_URL must be set in production.")

# Internal Railway network host (postgres.railway.internal or localhost) does not use SSL;
# external hosts like Supabase (*.supabase.co / pooler.supabase.com) require SSL.
_is_internal_db = any(h in DATABASE_URL_ENV for h in ["railway.internal", "localhost", "127.0.0.1"])
_ssl_require = not _is_internal_db

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL_ENV,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=_ssl_require,
    )
}

# ─── Static Files (WhiteNoise) ────────────────────────────────────────────────
# Insert WhiteNoise after SecurityMiddleware
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files: Use Cloudinary Cloud Storage when configured with valid secret
if IS_VALID_CLOUDINARY:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ─── CORS & CSRF ──────────────────────────────────────────────────────────────
def _normalize_origin(origin: str) -> str:
    origin = origin.strip().rstrip("/")
    if not origin:
        return ""
    if not (origin.startswith("http://") or origin.startswith("https://") or origin.startswith("tauri://")):
        # Prepend https:// if scheme is missing
        origin = f"https://{origin}"
    return origin

_raw_cors = os.environ.get("CORS_ALLOWED_ORIGINS", "")
_cors_list = [_normalize_origin(o) for o in _raw_cors.split(",") if o.strip()]

_default_origins = [
    "https://zamzamfoods.up.railway.app",
    "https://zamzamfood.up.railway.app",
    "https://zamzamfoods.vercel.app",
    "https://zamzamfoods-fontend.vercel.app",
    "https://zamzamfoods-frontend.vercel.app",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "http://localhost:1420",
    "http://localhost:5173",
]

for d in _default_origins:
    if d not in _cors_list:
        _cors_list.append(d)

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _cors_list
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://.*\.up\.railway\.app$",
    r"^https://.*\.railway\.app$",
    r"^tauri://.*$",
    r"^https?://tauri\.localhost$",
]
CORS_ALLOW_CREDENTIALS = True

_raw_csrf = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
_csrf_list = [_normalize_origin(o) for o in _raw_csrf.split(",") if o.strip()]
for d in _default_origins:
    if d not in _csrf_list:
        _csrf_list.append(d)

CSRF_TRUSTED_ORIGINS = _csrf_list

# ─── Security Headers ─────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT              = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE            = True
CSRF_COOKIE_SECURE               = True
SECURE_BROWSER_XSS_FILTER        = True
SECURE_CONTENT_TYPE_NOSNIFF      = True
X_FRAME_OPTIONS                  = "DENY"
SECURE_HSTS_SECONDS              = 31536000   # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS   = True
SECURE_HSTS_PRELOAD              = True
SECURE_PROXY_SSL_HEADER          = ("HTTP_X_FORWARDED_PROTO", "https")

# ─── Cookie Auth (HttpOnly JWT) ───────────────────────────────────────────────
# Override base.py defaults — always Secure in production
JWT_COOKIE_SECURE   = True
JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "None")  # "None" needed for cross-site Vercel → Koyeb

# ─── Production Logging ───────────────────────────────────────────────────────
LOGGING["handlers"]["console"]["level"] = "WARNING"
LOGGING["root"]["level"] = "WARNING"
