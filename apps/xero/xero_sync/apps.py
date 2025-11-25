from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class XeroSyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.xero.xero_sync'
    verbose_name = 'Xero Sync'
    
    def ready(self):
        """Start scheduler when Django app is ready."""
        # Only start scheduler in production or when explicitly enabled
        # Avoid starting in test mode or migrations
        import os
        import sys
        
        # Don't start scheduler during migrations or tests
        if 'migrate' in sys.argv or 'test' in sys.argv:
            return
        
        # Check if scheduler should be enabled
        from django.conf import settings
        if getattr(settings, 'XERO_SCHEDULER_ENABLED', True):
            try:
                from apps.xero.xero_sync.tasks import start_scheduler
                start_scheduler()
                logger.info("Xero scheduler initialized")
            except ImportError:
                logger.warning("APScheduler not installed. Scheduled tasks will not run. Install with: pip install apscheduler")
            except Exception as e:
                logger.error(f"Failed to start Xero scheduler: {str(e)}", exc_info=True)

