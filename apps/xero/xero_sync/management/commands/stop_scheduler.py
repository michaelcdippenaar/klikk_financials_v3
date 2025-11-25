"""
Management command to stop the Xero task scheduler.
"""
from django.core.management.base import BaseCommand
from apps.xero.xero_sync.tasks import stop_scheduler, scheduler


class Command(BaseCommand):
    help = 'Stop the Xero task scheduler'

    def handle(self, *args, **options):
        if scheduler and scheduler.running:
            stop_scheduler()
            self.stdout.write(self.style.SUCCESS('✓ Xero scheduler stopped successfully'))
        else:
            self.stdout.write(self.style.WARNING('Scheduler is not currently running'))

