"""
Django settings for ena_upload_ms project.

Generated by 'django-admin startproject' using Django 4.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import logging
from pathlib import Path
from os import environ
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.get(
    "DJANGO_SECRET_KEY",
    "1d9b8ddfd9766ee8c6e6-cf6a52053f-f904bca9d9-22f89e1c33de96dde50e",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (environ.get("DJANGO_DEBUG", "False")) == "True"
LOG_LEVEL = environ.get("DJANGO_LOG_LEVEL", "INFO")
LOG_SQL = False
LOG_SH = False

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "django_extensions",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "drf_auto_endpoint",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

# We only add the middleware if DJANGO_CORS_ALLOWED_ORIGINS env var is set
if environ.get("DJANGO_CORS_ALLOWED_ORIGINS"):
    MIDDLEWARE.append(
        "corsheaders.middleware.CorsMiddleware",
    )

MIDDLEWARE += [
    "django.middleware.common.CommonMiddleware",
]

# We only add the middleware if DJANGO_CSRF_TRUSTED_ORIGINS env var is set
if environ.get("DJANGO_CSRF_TRUSTED_ORIGINS"):
    MIDDLEWARE.append(
        "django.middleware.csrf.CsrfViewMiddleware",
    )

MIDDLEWARE += [
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ena_upload_ms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "ena_upload_ms.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": environ.get("POSTGRES_HOST", "db"),
        "PORT": environ.get("POSTGRES_PORT", "5432"),
        "NAME": environ.get("POSTGRES_DB", "ena"),
        "USER": environ.get("POSTGRES_USER", "ena"),
        "PASSWORD": environ.get("POSTGRES_PASSWORD"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-US"
TIME_ZONE = "Europe/Zurich"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = "/vol/web/static"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DISABLE_BROWSABLE_API = False
DISABLE_AUTH = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_METADATA_CLASS": "meta.serializers.APIMetadata",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_csv.renderers.CSVRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

if DISABLE_BROWSABLE_API:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework_csv.renderers.CSVRenderer",
    ]

if DISABLE_AUTH:
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = []

FIXTURE_DIRS = []

###
# SECURITY
###
ALLOWED_HOSTS = environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# CORS configuration
if environ.get("DJANGO_CORS_ALLOWED_ORIGINS"):
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = environ.get("DJANGO_CORS_ALLOWED_ORIGINS").split(",")
    CORS_ALLOW_HEADERS = default_headers + (
        "cache-control",
        "pragma",
        "expires",
    )
    CORS_EXPOSE_HEADERS = ["Content-Type"]
    CORS_ALLOW_CREDENTIALS = True

# CSRF configuration
if environ.get("DJANGO_CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = environ.get("DJANGO_CSRF_TRUSTED_ORIGINS").split(",")
    CSRF_USE_SESSIONS = False
    CSRF_COOKIE_HTTPONLY = False
    CSRF_COOKIE_SAMESITE = "Strict"

SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 1209600  # (1209600) default: 2 weeks in seconds

# PROD ONLY
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True

###
# LOGGING
###
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{name} {levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console"],
    },
    "loggers": {},
}
if LOG_SQL:
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }
if not LOG_SH:
    logging.getLogger("sh.command").setLevel(logging.WARNING)
    logging.getLogger("sh.stream_bufferer").setLevel(logging.WARNING)
    logging.getLogger("sh.process").setLevel(logging.WARNING)
    logging.getLogger("sh.streamwriter").setLevel(logging.WARNING)
    logging.getLogger("sh.streamreader").setLevel(logging.WARNING)


###
# Documentation
###
SPECTACULAR_SETTINGS = {
    "TITLE": "ENA Upload Microservice",
    "DESCRIPTION": "Microservice to simplify ENA uploads",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",  # shorthand to use the sidecar instead
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    # OTHER SETTINGS
}

###
# Tool specific settings
###
ENA_USERNAME = environ.get("ENA_USERNAME", None)
ENA_PASSWORD = environ.get("ENA_PASSWORD", None)
ENA_USE_DEV_ENDPOINT = (environ.get("ENA_USE_DEV_ENDPOINT", "True")) == "True"
ENA_ENDPOINT = (
    "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA"
    if ENA_USE_DEV_ENDPOINT
    else "https://www.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA"
)
ENA_BROWSER_URL = (
    "https://wwwdev.ebi.ac.uk/ena/browser/view"
    if ENA_USE_DEV_ENDPOINT
    else "https://www.ebi.ac.uk/ena/browser/view"
)
ENA_UPLOAD_FREQ_SECS = int(environ.get("ENA_UPLOAD_FREQ_SECS", 5))
TEMPLATE_DIR = "/templates"
DATA_DIR = "/data"
