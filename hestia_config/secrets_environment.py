# This file loads secret configuration values
# (SECRET_KEY, API keys, and similar credentials) into Django.
#
# We use the django-environ library to read these values from a .env file
# and convert them into operating system environment variables.
#
# This lets us:
#   • Keep secrets out of GitHub
#   • Use different settings for development vs production
#   • Use the same codebase everywhere

import environ
from pathlib import Path

env = environ.Env()

# Project root (the folder that contains manage.py and .env)
# BASE_DIR in settings/base.py does not exist yet when this file runs.
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(BASE_DIR / ".env")
