"""
Django settings for klikk_business_intelligence project.

This file is kept for backward compatibility but is deprecated.
Please use the settings package directly:

Set DJANGO_SETTINGS_MODULE to one of:
- klikk_business_intelligence.settings.development (default)
- klikk_business_intelligence.settings.staging
- klikk_business_intelligence.settings.production

Or set DJANGO_ENV environment variable and import from settings package:
- development (default)
- staging
- production
"""

# Import development settings by default for backward compatibility
from klikk_business_intelligence.settings.development import *
