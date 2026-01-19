"""
Production environment settings for klikk_business_intelligence project.

These settings are used for the production server.
IMPORTANT: Never commit sensitive production values to version control.
Use environment variables for all sensitive settings.
"""

from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
# MUST be set via environment variable in production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set in production!")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Update with your production server domain(s)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS environment variable must be set in production!")

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Production database credentials should come from environment variables

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'klikk_financials_prod'),
        'USER': os.environ.get('DB_USER', 'klikk_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes (connection pooling)
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Validate that database password is set
if not DATABASES['default']['PASSWORD']:
    raise ValueError("DB_PASSWORD environment variable must be set in production!")

# Update JWT signing key
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

# Security settings for production
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SESSION_COOKIE_SECURE = True  # Only send session cookies over HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF cookies over HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Xero Scheduler Configuration
XERO_SCHEDULER_ENABLED = True  # Enabled for production
