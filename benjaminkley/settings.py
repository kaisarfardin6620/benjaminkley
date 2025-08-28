# benjaminkley/settings.py

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from a .env file (for local development)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- CORE SETTINGS ---
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set. Please create a .env file.")

# DEBUG mode is controlled by an environment variable.
# It will be 'False' in production (Railway/AWS) by default.
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# --- HOSTING & SECURITY ---
# Start with a base list for local development.
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# In production, Railway provides a RAILWAY_STATIC_URL which contains the hostname.
# This code will automatically add it to the list if it exists.
RAILWAY_HOSTNAME = os.getenv('RAILWAY_STATIC_URL')
if RAILWAY_HOSTNAME:
    # The hostname is the part after 'https://'
    ALLOWED_HOSTS.append(RAILWAY_HOSTNAME.split('//')[1])

# CSRF is essential for security.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if '.' in host]
CSRF_TRUSTED_ORIGINS.extend(['http://127.0.0.1:8001', 'http://localhost:8001'])

# --- APPLICATIONS & MIDDLEWARE ---
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    # Your apps
    'authentication',
    'contact_support',
    'scans',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'benjaminkley.urls'
WSGI_APPLICATION = 'benjaminkley.wsgi.application'

# --- DATABASE CONFIGURATION (FLEXIBLE) ---
DATABASES = {
    'default': dj_database_url.config(
        # In production (Railway), it uses the DATABASE_URL env variable.
        # Locally, if DATABASE_URL is not in your .env, it falls back to SQLite.
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- STATIC & MEDIA FILES ---
AI_MODELS_DIR = BASE_DIR / 'ai_models'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- CELERY AND REDIS CONFIGURATION (FLEXIBLE) ---
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# --- ALL OTHER SETTINGS ---
TEMPLATES = [ # ... (Your existing config is fine)
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
        'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',],},
    },
]
AUTH_PASSWORD_VALIDATORS = [ # ... (Your existing config is fine)
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = { # ... (Your existing config is fine)
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '100/day', 'user': '1000/day'}
}
SIMPLE_JWT = { # ... (Your existing config is fine)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),'REFRESH_TOKEN_LIFETIME': timedelta(days=1), 'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True, 'UPDATE_LAST_LOGIN': False, 'ALGORITHM': 'HS256', 'SIGNING_KEY': SECRET_KEY, 'VERIFYING_KEY': None, 'AUDIENCE': None, 'ISSUER': None, 'JWK_URL': None, 'LEEWAY': 0, 'AUTH_HEADER_TYPES': ('Bearer',), 'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION', 'USER_ID_FIELD': 'id', 'USER_ID_CLAIM': 'user_id', 'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule', 'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',), 'TOKEN_TYPE_CLAIM': 'token_type', 'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser', 'JTI_CLAIM': 'jti', 'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp', 'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5), 'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1), 'TOKEN_OBTAIN_SERIALIZER': 'authentication.serializers.MyTokenObtainPairSerializer', 'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer', 'TOKEN_VERIFY_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenVerifySerializer', 'TOKEN_BLACKLIST_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenBlacklistSerializer', 'TOKEN_SLIDE_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer',
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER')

# --- CORS Configuration ---
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS # Use the same list for CORS
CORS_ALLOW_CREDENTIALS = True