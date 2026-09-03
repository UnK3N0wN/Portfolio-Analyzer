import os
from pathlib import Path
from dotenv import load_dotenv

# Django settings for portfolio_ai project.

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

_secret_key = os.getenv('DJANGO_SECRET_KEY')
if not _secret_key:
    if DEBUG:
        # Fine for local dev only — never used if DJANGO_SECRET_KEY is set.
        _secret_key = 'dev-insecure-secret-key-do-not-use-in-production'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY is not set. Refusing to start with DEBUG=False '
            'and no secret key configured — set DJANGO_SECRET_KEY in the '
            'environment before deploying.'
        )
SECRET_KEY = _secret_key

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'django_celery_beat',
    'users.apps.UsersConfig',
    'portfolio.apps.PortfolioConfig',
    'stocks.apps.StocksConfig',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# For URL configuration and WSGI application

ROOT_URLCONF = 'portfolio_ai.urls'
WSGI_APPLICATION = 'portfolio_ai.wsgi.application'

# For templates - using Django's default template engine with templates directory at BASE_DIR/templates

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

#  For Database - using db.sqlite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'portfolio_ai'),
        'USER': os.getenv('DB_USER', 'portfolio_ai'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        # Keep connections alive between requests instead of reconnecting
        # every time — cheap win once you're not on SQLite anymore.
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', 60)),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Kolkata')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Force Django to bypass Redis and use memory/database when running tests
    
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

STOCK_CACHE_TIMEOUT = int(os.getenv('STOCK_CACHE_TIMEOUT', 900))
ANTHROPIC_API_KEY   = os.getenv('ANTHROPIC_API_KEY', '')
GROQ_API_KEY        = os.getenv('GROQ_API_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_SSL_REDIRECT          = True
    SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE        = True
    CSRF_COOKIE_SECURE           = True
    SECURE_HSTS_SECONDS          = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True
    SECURE_CONTENT_TYPE_NOSNIFF  = True
    X_FRAME_OPTIONS              = 'DENY'

from celery.schedules import crontab  # noqa: E402

CELERY_BROKER_URL     = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT   = ['json']
CELERY_TASK_SERIALIZER  = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 90

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CELERY_BEAT_SCHEDULE = {
    'update-holding-prices': {
        'task': 'portfolio.tasks.update_all_holding_prices',
        'schedule': crontab(minute='*/10'),
    },
    'check-price-alerts': {
        'task': 'portfolio.tasks.check_all_price_alerts',
        'schedule': crontab(minute='*/5'),
    },
    'update-watchlist-prices': {
        'task': 'portfolio.tasks.update_all_watchlist_prices',
        'schedule': crontab(minute='*/15'),
    },
    'create-daily-snapshots': {
        'task': 'portfolio.tasks.create_daily_snapshots',
        'schedule': crontab(hour=23, minute=55),
    },
}