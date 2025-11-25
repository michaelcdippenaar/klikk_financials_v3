from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run process tree examples - demonstrates ProcessTreeBuilder, ProcessTreeManager, and ProcessTreeInstance usage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--example',
            type=str,
            choices=['build_and_save', 'xero_sync', 'execute_by_name', 'dependent_trees', 'sibling_trees', 'trigger_usage', 'trigger_subscriptions'],
            default='build_and_save',
            help='Which example to run (default: build_and_save)',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='Xero tenant ID to use (for xero_sync example)',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Execute the process tree after building (for build_and_save example)',
        )

    def handle(self, *args, **options):
        # Import here to avoid circular import issues during command discovery
        from apps.xero.xero_sync.process_manager.examples import (
            example_build_and_save_tree,
            example_xero_sync_tree,
            example_execute_by_name,
            example_dependent_trees,
            example_sibling_trees,
            example_trigger_usage,
            example_trigger_subscriptions,
        )
        
        example = options.get('example', 'build_and_save')
        tenant_id = options.get('tenant_id')
        
        examples_map = {
            'build_and_save': example_build_and_save_tree,
            'xero_sync': example_xero_sync_tree,
            'execute_by_name': example_execute_by_name,
            'dependent_trees': example_dependent_trees,
            'sibling_trees': example_sibling_trees,
            'trigger_usage': example_trigger_usage,
            'trigger_subscriptions': example_trigger_subscriptions,
        }
        
        example_func = examples_map.get(example)
        
        if not example_func:
            self.stdout.write(self.style.ERROR(f'Unknown example: {example}'))
            self.stdout.write(self.style.WARNING('Available examples:'))
            for ex_name in examples_map.keys():
                self.stdout.write(f'  - {ex_name}')
            return
        
        self.stdout.write(self.style.SUCCESS(f'Running example: {example}'))
        self.stdout.write('=' * 70)
        
        try:
            if example == 'xero_sync' and tenant_id:
                self.stdout.write(self.style.WARNING(f'Note: example_xero_sync_tree currently has hardcoded tenant_id'))
                self.stdout.write(self.style.WARNING(f'You provided tenant_id: {tenant_id}, but it may not be used'))
            
            # Pass execute flag to build_and_save example
            if example == 'build_and_save' and options.get('execute'):
                example_func(execute=True)
            else:
                example_func()
            
            self.stdout.write('=' * 70)
            self.stdout.write(self.style.SUCCESS('Example executed successfully'))
        except Exception as e:
            self.stdout.write('=' * 70)
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

