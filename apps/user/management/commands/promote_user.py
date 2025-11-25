"""
Management command to promote a user to staff or superuser.

Usage:
    python manage.py promote_user <username> --staff
    python manage.py promote_user <username> --superuser
    python manage.py promote_user <username> --staff --superuser
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Promote a user to staff or superuser status'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to promote')
        parser.add_argument(
            '--staff',
            action='store_true',
            help='Grant staff status (allows admin login)',
        )
        parser.add_argument(
            '--superuser',
            action='store_true',
            help='Grant superuser status (all permissions)',
        )
        parser.add_argument(
            '--remove-staff',
            action='store_true',
            help='Remove staff status',
        )
        parser.add_argument(
            '--remove-superuser',
            action='store_true',
            help='Remove superuser status',
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')

        changes_made = False

        # Grant staff status
        if options['staff']:
            if not user.is_staff:
                user.is_staff = True
                changes_made = True
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Granted staff status to "{username}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already has staff status')
                )

        # Grant superuser status
        if options['superuser']:
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True  # Superusers must be staff
                changes_made = True
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Granted superuser status to "{username}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already has superuser status')
                )

        # Remove staff status
        if options['remove_staff']:
            if user.is_staff:
                if user.is_superuser:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Cannot remove staff status from superuser "{username}". '
                            'Remove superuser status first.'
                        )
                    )
                else:
                    user.is_staff = False
                    changes_made = True
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Removed staff status from "{username}"')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" does not have staff status')
                )

        # Remove superuser status
        if options['remove_superuser']:
            if user.is_superuser:
                user.is_superuser = False
                changes_made = True
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Removed superuser status from "{username}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" does not have superuser status')
                )

        # Save changes
        if changes_made:
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ User "{username}" updated successfully')
            )
        else:
            if not any([options['staff'], options['superuser'], 
                       options['remove_staff'], options['remove_superuser']]):
                self.stdout.write(
                    self.style.WARNING(
                        '\nNo action specified. Use --staff, --superuser, '
                        '--remove-staff, or --remove-superuser'
                    )
                )

        # Display current status
        self.stdout.write(f'\nCurrent status for "{username}":')
        self.stdout.write(f'  Staff: {user.is_staff}')
        self.stdout.write(f'  Superuser: {user.is_superuser}')
        self.stdout.write(f'  Active: {user.is_active}')


