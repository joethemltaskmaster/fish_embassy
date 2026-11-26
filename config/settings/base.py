from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# ─── Core Settings ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

# ─── Host & Security Settings ───────────────────────────────

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Render automatically provides the external hostname via this env var.
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    # Add the exact Render domain (e.g. rao-app-gorm.onrender.com)
    ALLOWED_HOSTS.append(render_hostname)
    # Also add the wildcard for any internal Render health checks
    ALLOWED_HOSTS.append(".onrender.com")

# Ensure CSRF works over HTTPS on Render
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8000").split(",") if o.strip()]
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")

# Tell Django that Render's proxy terminates SSL.
# Without this, Django thinks the request is insecure and may redirect you in a loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ─── Applications ───────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventory",
    "purchasing",
    "sales",
    "costing",
    "audit",
    "analytics",
    "business_ai",
]

# ─── Middleware (WhiteNoise added) ──────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # <-- Added for Render Static Files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Database ───────────────────────────────────────────────
# Use Render's DATABASE_URL if available, otherwise fallback to local
if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "rao_db"),
            "USER": os.environ.get("POSTGRES_USER", "rao"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "YOUR_STRONG_PASSWORD"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
"YOUR_STRONG_PASSWORD"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Authentication & Routing ───────────────────────────────
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard_index"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# ─── Static Files (WhiteNoise configuration) ────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Whitenoise compression for production
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Rule Register ──────────────────────────────────────────
RAO_EXPIRY_WARNING_DAYS = 30
RAO_BASE_UNIT = "carton"
RAO_ALLOW_PARTIAL_CARTONS = False
RAO_COSTING_METHOD = "average"
RAO_CURRENCY = "NGN"
RAO_CURRENCY_SYMBOL = "₦"
RAO_DEFAULT_LOCATION_CODE = "MAIN"

# ─── Production Security (Render) ───────────────────────────
if not DEBUG:
    # Render provides SSL at the proxy level
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Force all traffic to HTTPS
    SECURE_SSL_REDIRECT = True

    # Secure Cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HTTP Strict Transport Security (HSTS)
    # Tells browsers to always use HTTPS for 1 year (31536000 seconds)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True