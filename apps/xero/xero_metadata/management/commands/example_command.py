from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Example management command'

    def add_arguments(self, parser):
        # Add command arguments here
        pass

    def handle(self, *args, **options):
        # Command logic here
        self.stdout.write(self.style.SUCCESS('Command executed successfully'))

