"""
Django settings package for klikk_business_intelligence project.

This package contains environment-specific settings:
- base.py: Common settings shared across all environments
- development.py: Development environment settings
- staging.py: Staging environment settings
- production.py: Production environment settings

Usage:
    Set DJANGO_SETTINGS_MODULE environment variable to:
    - klikk_business_intelligence.settings.development (for development)
    - klikk_business_intelligence.settings.staging (for staging)
    - klikk_business_intelligence.settings.production (for production)
    
    Or set DJANGO_ENV environment variable:
    - development (default)
    - staging
    - production
"""

import os

# Default to development settings when settings package is imported directly
# This allows 'klikk_business_intelligence.settings' to work out of the box
from .base import *

env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
elif env == 'staging':
    from .staging import *
else:
    from .development import *
