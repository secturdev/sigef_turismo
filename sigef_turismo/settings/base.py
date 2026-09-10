import os
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

env_name = "prod" if "prod" in os.getenv("DJANGO_SETTINGS_MODULE", "") else "dev"
env_file = BASE_DIR / f".env/.env.{env_name}"

if not env_file.exists():
    raise ImproperlyConfigured(
        f"Archivo de entorno requerido no encontrado: {env_file}. "
        f"Crea el archivo a partir de .env.example antes de iniciar."
    )

environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_tables2",
    "axes",
    "csp",
    "mozilla_django_oidc",
]

LOCAL_APPS = [
    "apps.landingpage",
    "apps.autenticacion",
    "apps.expediente",
    "apps.muestras",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "autenticacion.Usuario"

# Documentos privados.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.autenticacion.middleware.OIDCCanonicalOriginMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "sigef_turismo.urls"

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
            "builtins": ["django.templatetags.static"],
        },
    },
]

WSGI_APPLICATION = "sigef_turismo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE"),
        "OPTIONS": {"connect_timeout": 10},
    }
}

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/inicio/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/inicio/"

# Llave Tabasco (OIDC).
LLAVE_TABASCO_ENABLED = env.bool("LLAVE_TABASCO_ENABLED", default=False)
LLAVE_TABASCO_ISSUER = env("LLAVE_TABASCO_ISSUER", default="")
LLAVE_TABASCO_CLIENT_ID = env("LLAVE_TABASCO_CLIENT_ID", default="")
LLAVE_TABASCO_CLIENT_SECRET = env("LLAVE_TABASCO_CLIENT_SECRET", default="")

_llave_issuer = LLAVE_TABASCO_ISSUER.rstrip("/")
OIDC_RP_CLIENT_ID = LLAVE_TABASCO_CLIENT_ID
OIDC_RP_CLIENT_SECRET = LLAVE_TABASCO_CLIENT_SECRET
OIDC_OP_AUTHORIZATION_ENDPOINT = (
    f"{_llave_issuer}/protocol/openid-connect/auth" if _llave_issuer else ""
)
OIDC_OP_TOKEN_ENDPOINT = (
    f"{_llave_issuer}/protocol/openid-connect/token" if _llave_issuer else ""
)
OIDC_OP_USER_ENDPOINT = (
    f"{_llave_issuer}/protocol/openid-connect/userinfo" if _llave_issuer else ""
)
OIDC_OP_JWKS_ENDPOINT = (
    f"{_llave_issuer}/protocol/openid-connect/certs" if _llave_issuer else ""
)
OIDC_OP_LOGOUT_ENDPOINT = (
    f"{_llave_issuer}/protocol/openid-connect/logout" if _llave_issuer else ""
)
OIDC_OP_LOGOUT_URL_METHOD = "apps.autenticacion.oidc.provider_logout"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
OIDC_STORE_ID_TOKEN = True
OIDC_CREATE_USER = True
OIDC_CALLBACK_CLASS = "apps.autenticacion.views.LlaveTabascoCallbackView"
# Tolerancia de reloj OIDC (iat).
OIDC_CLOCK_SKEW = env.int("OIDC_CLOCK_SKEW", default=120)
# Diagnóstico de atributos recibidos desde Llave Tabasco. Se habilita por defecto
# únicamente en desarrollo; puede controlarse con OIDC_LOG_CLAIMS=true/false.
OIDC_LOG_CLAIMS = env.bool("OIDC_LOG_CLAIMS", default=env_name == "dev")
# Origen público registrado en Llave Tabasco. Evita que el callback cambie
# entre alias del mismo servidor (por ejemplo, localhost y 127.0.0.1).
OIDC_CANONICAL_ORIGIN = env("OIDC_CANONICAL_ORIGIN", default="").rstrip("/")

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE"),
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7200
SESSION_SAVE_EVERY_REQUEST = True

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.autenticacion.oidc.LlaveTabascoOIDCBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_LOCKOUT_URL = "/lockout/"

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "connect-src": ["'self'"],
    }
}

FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE")
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE")
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.int("DATA_UPLOAD_MAX_NUMBER_FIELDS")
