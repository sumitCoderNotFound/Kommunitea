"""Sync the UK provider list from a free public CSV (UKRLP/OfS/data.ac.uk export).

Usage: python manage.py sync_universities --url "<provider CSV URL>"
"""
from django.core.management.base import BaseCommand
from study_match.sync import sync_universities


class Command(BaseCommand):
    help = "Upsert UK universities/providers from a public CSV source."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="URL to a public provider CSV")

    def handle(self, *args, **opts):
        log = sync_universities(url=opts["url"])
        self.stdout.write(self.style.SUCCESS(
            f"Provider sync {log.status}: +{log.inserted_records} / ~{log.updated_records} of {log.total_records}."
            + (f" Error: {log.error_message}" if log.error_message else "")
        ))
