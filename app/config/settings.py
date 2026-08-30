"""
Django settings for Docker Registry Platform.
"""

import os
from pathlib import Path
import dj_database_url
from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DEBUG', 'True') == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Project apps
    'accounts',
    'repositories',
    'explore',
    'analytics',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.ForcePasswordChangeMiddleware',
    'core.middleware.RequestLoggingMiddleware',
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
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Uses DATABASE_URL env var if set (PostgreSQL in Docker), otherwise SQLite
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')
    )
}

# Custom User model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Bootstrap uses "alert-danger" for errors, not Django's default "error" tag
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'explore'
LOGOUT_REDIRECT_URL = '/login/'

# Admin setup (setup_admin management command)
ADMIN_PASSWORD_FILE = os.environ.get('ADMIN_PASSWORD_FILE', str(BASE_DIR / 'admin_password.txt'))

# External services
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')
REGISTRY_URL = os.environ.get('REGISTRY_URL', 'http://localhost:5000')
REGISTRY_USERNAME = os.environ.get('REGISTRY_USERNAME', 'admin')
REGISTRY_PASSWORD = os.environ.get('REGISTRY_PASSWORD', 'Admin123')
REGISTRY_AUTH_ISSUER = os.environ.get('REGISTRY_AUTH_ISSUER', 'uks-registry-auth')
REGISTRY_AUTH_SERVICE = os.environ.get('REGISTRY_AUTH_SERVICE', 'uks-registry')
REGISTRY_AUTH_KEY_PATH = os.environ.get('REGISTRY_AUTH_KEY_PATH', '/auth/registry-auth.key')
REGISTRY_TOKEN_TTL = 300

# Logging
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOG_MAX_BYTES = 1024 * 1024 * 5
LOG_BACKUP_COUNT = 5

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'rename_fields': {'asctime': 'timestamp', 'levelname': 'level', 'name': 'logger'},
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'app_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': LOG_MAX_BYTES,
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'json',
        },
        'access_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'access.log',
            'maxBytes': LOG_MAX_BYTES,
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': LOG_MAX_BYTES,
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'json',
        },
    },
    'loggers': {
        'core.request': {
            'handlers': ['console', 'access_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'app_file', 'error_file'],
        'level': 'INFO',
    },
}
