from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Populate Japanese car categories and auctions (skipping existing entries)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='Populate for a specific user ID only. If omitted, populates for all users.'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        if user_id:
            call_command('populate_japan_data', user_id=user_id)
        else:
            call_command('populate_japan_data')
