"""
Django settings for Payvora VTU Platform.
Environment variables are loaded from .env via python-dotenv.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / '.env')

# ── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-_8^(m5$-)0^1oni17&am4$(g01g$*d%n%_f9lyx8&_d0!+%zgc'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_hosts = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]

# ── Application definition ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third Party
    'rest_framework',

    # Custom Modular Apps
    'apps.auth.apps.AuthConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.public.apps.PublicConfig',
]

# Integrate Cloudinary Storage if configured in env
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')
if CLOUDINARY_URL:
    INSTALLED_APPS.insert(0, 'cloudinary_storage')
    INSTALLED_APPS.append('cloudinary')
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'string_if_invalid': '',
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Database ────────────────────────────────────────────────────────────────
# PostgreSQL via DATABASE_URL fallback to local SQLite
db_from_env = dj_database_url.config(conn_max_age=600)
if db_from_env:
    DATABASES = {'default': db_from_env}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password validation ─────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('TIME_ZONE', 'Africa/Lagos')
USE_I18N = True
USE_TZ = True

# ── Static & Media Files ────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / os.environ.get('STATIC_ROOT', 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Authentication redirects ────────────────────────────────────────────────
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_overview'
LOGOUT_REDIRECT_URL = 'landing'

# ── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# ── Celery configuration ────────────────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ── REST Framework ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ── Third-Party API Keys ────────────────────────────────────────────────────
MONNIFY_API_KEY = os.environ.get('MONNIFY_API_KEY', '')
MONNIFY_SECRET_KEY = os.environ.get('MONNIFY_SECRET_KEY', '')
MONNIFY_CONTRACT_CODE = os.environ.get('MONNIFY_CONTRACT_CODE', '')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
BIGISUB_API_KEY = os.environ.get('BIGISUB_API_KEY', '')

# ── Production security ─────────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
