"""
Staging environment settings for klikk_business_intelligence project.

These settings are used for the staging server.
"""

from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
# In staging, use environment variable or a secure key
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-staging-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Update with your staging server domain
# Include: IP address, hostname, domain name (if applicable), localhost, and 127.0.0.1
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,192.168.1.236').split(',')

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'klikk_financials',
        'USER': 'klikk_user',
        'PASSWORD': 'StrongPasswordHere',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes (connection pooling)
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Update JWT signing key
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

# Security settings for staging
SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
CSRF_COOKIE_SECURE = False  # Set to True if using HTTPS

# Xero Scheduler Configuration
XERO_SCHEDULER_ENABLED = True  # Enabled for staging
