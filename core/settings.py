from pathlib import Path
from decouple import config, Csv


# Build paths inside the project like this: BASE_DIR / "subdir".

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!

SECRET_KEY = config("SECRET_KEY")


# SECURITY WARNING: don"t run with debug turned on in production!

DEBUG = config("DEBUG", cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "unfold",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "django_cotton",
    "django_tailwind_cli",

    "core",
    "apps.home",
    "apps.account",
    "apps.billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"


# Database

if config("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": config("POSTGRES_HOST"),
            "PORT": config("POSTGRES_PORT"),
            "NAME": config("POSTGRES_DB"),
            "USER": config("POSTGRES_USER"),
            "PASSWORD": config("POSTGRES_PASSWORD"),
            "CONN_MAX_AGE": 120,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation

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

LANGUAGE_CODE = "pt-BR"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_L10N = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}


# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# User Model

AUTH_USER_MODEL = "account.User"

AUTHENTICATION_BACKENDS = ["apps.account.backends.CustomBackend"]

SESSION_COOKIE_AGE = 60 * 60 * 24

LOGIN_URL = "/entrar"


# Email

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = config("EMAIL_HOST")

EMAIL_PORT = config("EMAIL_PORT")

EMAIL_HOST_USER = config("EMAIL_USER")

EMAIL_HOST_PASSWORD = config("EMAIL_PASSWORD")

EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool)

EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool)

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# HTTPS / SSL

if not DEBUG:
	CSRF_COOKIE_SECURE = True
	SECURE_SSL_REDIRECT = True
	SESSION_COOKIE_SECURE = True
	SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Django Cotton

COTTON_DIR = "components"


# Django Debug Toolbar

if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")


# Asaas

ASAAS_API_KEY = config("ASAAS_API_KEY")

ASAAS_ACCESS_TOKEN = config("ASAAS_ACCESS_TOKEN")

ASAAS_BASE_URL = config("ASAAS_BASE_URL")
