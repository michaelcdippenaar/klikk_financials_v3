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
        # For gunicorn with multiple workers, use 0 to disable connection pooling
        # Each worker will manage its own connections
        'CONN_MAX_AGE': 0,  # Disable persistent connections for gunicorn workers
        'OPTIONS': {
            'connect_timeout': 10,
            # Additional options for better connection handling
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
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

# Google Cloud credentials path (for BigQuery exports)
# MUST be set via environment variable: GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable must be set in production!")

# Xero Scheduler Configuration
XERO_SCHEDULER_ENABLED = True  # Enabled for production
