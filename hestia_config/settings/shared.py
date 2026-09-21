"""Opt-in shared PostgreSQL for team development; not deployment settings.

Use --settings=hestia_config.settings.shared explicitly. Default development
and its tests continue to use local SQLite.
"""
from django.core.exceptions import ImproperlyConfigured

from .development import *

# Do not render database connection details in browser error pages.
DEBUG = False
DATABASES = {"default": env.db("DATABASE_URL")}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Shared settings require a PostgreSQL DATABASE_URL.")
DATABASES["default"].setdefault("OPTIONS", {}).update(
    sslmode="require", connect_timeout=10
)
DATABASES["default"]["CONN_MAX_AGE"] = 0

# Staging must never pretend console output is delivered email.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
ACCOUNT_SIGNUP_ENABLED = bool(
    env.bool("STAGING_SIGNUP_ENABLED", default=False)
    and EMAIL_HOST and env("DEFAULT_FROM_EMAIL", default="")
    and env("ACCOUNT_PUBLIC_ORIGIN", default="").startswith("https://")
)
