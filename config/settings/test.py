"""
Test settings for Zamzam Foods — runs isolated automated tests using in-memory SQLite.
Prevents automated tests from touching or modifying the live production database.
"""
import os
from .base import *

DEBUG = False

# Isolated In-Memory Database for fast, deterministic unit & integration tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# PBKDF2 hasher with 1 iteration for fast test execution that satisfies pbkdf2 prefix assertions
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Ensure media directory is temporary during tests
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

# Disable background logging in tests
LOGGING = {}
