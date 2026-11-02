from .base import *  # noqa: F401,F403

DEBUG = False

# Real Postgres only — row locking and triggers do not behave the same on SQLite.
DATABASES["default"]["TEST"] = {"NAME": "test_rao"}  # noqa: F405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests must fail loudly on any query that would have been DB-specific.