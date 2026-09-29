"""
WSGI config for Zamzam Foods project.
Reads DJANGO_ENV to select the correct settings module.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Resolve backend directory and load .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Add backend directory to sys.path so apps can be imported
sys.path.insert(0, str(BASE_DIR))

# Select settings module based on DJANGO_ENV (defaults to production in wsgi)
django_env = os.environ.get("DJANGO_ENV", "production").lower()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{django_env}")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
