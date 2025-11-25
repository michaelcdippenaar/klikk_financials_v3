from django.core.management.base import BaseCommand
from apps.xero.xero_data.models import XeroJournalsSource
from apps.xero.xero_core.models import XeroTenant


class Command(BaseCommand):
    help = 'Delete all journals from XeroJournalsSource. Optionally filter by tenant_id.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='Optional: Delete journals for a specific tenant_id only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        force = options.get('force', False)
        
        # Build query
        queryset = XeroJournalsSource.objects.all()
        if tenant_id:
            try:
                tenant = XeroTenant.objects.get(tenant_id=tenant_id)
                queryset = queryset.filter(organisation=tenant)
                self.stdout.write(f"Filtering by tenant_id: {tenant_id}")
            except XeroTenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant {tenant_id} not found"))
                return
        
        # Count records
        total_count = queryset.count()
        processed_count = queryset.filter(processed=True).count()
        unprocessed_count = queryset.filter(processed=False).count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING("No journals found to delete"))
            return
        
        # Show summary
        self.stdout.write(self.style.WARNING(f"\nSummary:"))
        self.stdout.write(f"  Total journals: {total_count}")
        self.stdout.write(f"  Processed: {processed_count}")
        self.stdout.write(f"  Unprocessed: {unprocessed_count}")
        
        if tenant_id:
            self.stdout.write(f"\nThis will delete ALL journals for tenant {tenant_id}")
        else:
            self.stdout.write(f"\nThis will delete ALL journals for ALL tenants")
        
        # Confirm deletion
        if not force:
            confirm = input("\nAre you sure you want to delete these journals? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("Deletion cancelled"))
                return
        
        # Delete
        deleted_count = queryset.delete()[0]
        
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully deleted {deleted_count} journal(s) from XeroJournalsSource"))

