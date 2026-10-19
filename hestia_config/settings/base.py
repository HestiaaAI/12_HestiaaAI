from pathlib import Path

from hestia_config.secrets_environment import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env("SECRET_KEY")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")

# A6 Person 2 — local Hugging Face Brain Dump (shared contract with ai_prototype.ipynb)
HESTIA_BRAIN_DUMP_BACKEND = env("HESTIA_BRAIN_DUMP_BACKEND", default="local")
HESTIA_TASK_BREAKDOWN_CALLABLE = env("HESTIA_TASK_BREAKDOWN_CALLABLE", default="")
HF_TOKEN = env("HF_TOKEN", default="")
HF_BRAIN_DUMP_MODEL = env(
    "HF_BRAIN_DUMP_MODEL",
    default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
)
HF_BRAIN_DUMP_DEVICE = env("HF_BRAIN_DUMP_DEVICE", default="cpu")
HF_BRAIN_DUMP_MAX_NEW_TOKENS = env.int("HF_BRAIN_DUMP_MAX_NEW_TOKENS", default=220)
HF_BRAIN_DUMP_SHOT_MODE = env("HF_BRAIN_DUMP_SHOT_MODE", default="few")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "households",
    "intake",
    "inventory",
    "workflows",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "api.middleware.ApiAccessMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "households.access.AssignmentAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hestia_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hestia_config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static files"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
# Return to home after a direct sign-in; honor an explicit safe local next URL.
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "accounts:login"
PUBLIC_API_VIEW_NAMES = {"api:chart-priorities"}

# Keep the existing User model and allauth for later Google OAuth integration.
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_ADAPTER = "households.account_adapter.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "accounts:login"
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = "accounts:login"
ACCOUNT_SIGNUP_ENABLED = True
SOCIALACCOUNT_ADAPTER = "households.social_adapter.GoogleSocialAccountAdapter"
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": ([{
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": "",
        }] if GOOGLE_OAUTH_ENABLED else []),
        "SCOPE": ["profile", "email"],
        "OAUTH_PKCE_ENABLED": True,
    }
}
ACCOUNT_PUBLIC_ORIGIN = env("ACCOUNT_PUBLIC_ORIGIN", default="http://127.0.0.1:8012")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Hestia <noreply@example.invalid>")
