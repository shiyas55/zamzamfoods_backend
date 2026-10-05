"""
Base Django settings for Zamzam Foods Business Management System.
These settings are shared across all environments (development, production).
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Security key must be supplied via environment variable in production
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "fallback-insecure-dev-key-zamzam-foods-2026")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party applications
    "cloudinary_storage",
    "cloudinary",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # Required for refresh token revocation
    "corsheaders",
    "drf_spectacular",

    # Zamzam domain applications
    "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.routes.apps.RoutesConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.products.apps.ProductsConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.deliveries.apps.DeliveriesConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.credits.apps.CreditsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.whatsapp.apps.WhatsAppConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.common.middleware.MaintenanceModeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Cloudinary Cloud Media Storage ───────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "eil4vufk")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "248754147641721")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
}

if CLOUDINARY_API_SECRET or CLOUDINARY_URL:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Cookie-based JWT (HttpOnly) — primary for browser clients
        "apps.common.authentication.CookieJWTAuthentication",
        # Bearer header fallback for Swagger / Postman / non-browser clients
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# ─── SimpleJWT Settings ──────────────────────────────────────────────────────
# Access token: 15 min  |  Refresh token: 30 days
# Persistent login duration (for Driver/Manager) is controlled separately via
# the DeviceSession model and the PERSISTENT_LOGIN_DAYS env variable.
SIMPLE_JWT = {
    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "30"))),

    # Rotate & blacklist: every refresh call issues a new refresh token;
    # the old one is blacklisted so it cannot be replayed.
    "ROTATE_REFRESH_TOKENS":   True,
    "BLACKLIST_AFTER_ROTATION": True,

    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM":   "HS256",
    # IMPORTANT: JWT_SECRET_KEY must be set in production .env — never hardcode it.
    "SIGNING_KEY": os.environ.get("JWT_SECRET_KEY", SECRET_KEY),

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ─── JWT Cookie Settings ─────────────────────────────────────────────────────
# These control how the HttpOnly cookies are configured.
# In development: JWT_COOKIE_SECURE=False  (HTTP is fine)
# In production:  JWT_COOKIE_SECURE=True   (HTTPS required)
JWT_COOKIE_SECURE   = os.environ.get("JWT_COOKIE_SECURE", "False").lower() == "true"
JWT_COOKIE_HTTPONLY = True   # Always True — JS must never read these cookies
JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")

# ─── Persistent Login Settings ───────────────────────────────────────────────
# How long Driver / Manager devices stay logged in without re-entering password.
# Configurable: 1, 2, or 3 days.  Does NOT affect access/refresh token lifetimes.
PERSISTENT_LOGIN_DAYS = int(os.environ.get("PERSISTENT_LOGIN_DAYS", "3"))

# drf-spectacular settings for OpenAPI documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Zamzam Foods Business Management API",
    "DESCRIPTION": "Secure full-stack REST API for Zamzam Foods (Kubbus, Romali distribution, delivery routes, payments & credit ledger).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] [{levelname}] [{name}:{lineno}] - {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# ─── Meta WhatsApp Cloud API (WhatsApp Business Platform) ─────────────────────
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "zamzam_verify_token_2026")
