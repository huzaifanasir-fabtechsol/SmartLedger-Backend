from django.core.management.base import BaseCommand, CommandError

from apps.account.models import User
from apps.reports.filed_history import load


class Command(BaseCommand):
    help = ('Load the company profile and the five filed fiscal years (terms 1-5) from apps/reports/filed_history.py '
            'and open term 6 (2026) by roll-forward.')

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Email of the company user to load the history into')
        parser.add_argument('--replace', action='store_true', help='Delete and rebuild terms that already exist')
        parser.add_argument('--no-roll', action='store_true', help='Do not open term 6')

    def handle(self, *args, email, replace, no_roll, **options):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'No user with email {email}')
        load(user, replace=replace, roll=not no_roll, log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS('Done.'))
