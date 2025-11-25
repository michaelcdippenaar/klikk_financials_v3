from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Example management command - demonstrates Xero sync tree usage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-example',
            action='store_true',
            help='Run the example_xero_sync_tree function',
        )

    def handle(self, *args, **options):
        if options['run_example']:
            # Import here to avoid circular import issues during command discovery
            from apps.xero.xero_sync.process_manager.examples import example_xero_sync_tree
            
            self.stdout.write(self.style.WARNING('Running example_xero_sync_tree...'))
            try:
                example_xero_sync_tree()
                self.stdout.write(self.style.SUCCESS('Example executed successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
        else:
            self.stdout.write(self.style.SUCCESS('Command executed successfully'))
            self.stdout.write(self.style.WARNING('Use --run-example to execute example_xero_sync_tree'))

