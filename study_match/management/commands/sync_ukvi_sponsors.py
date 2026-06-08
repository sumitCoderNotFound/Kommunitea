"""Sync UKVI student sponsor status from the GOV.UK register CSV.

Usage: python manage.py sync_ukvi_sponsors --url "<GOV.UK register CSV URL>"
Download the latest CSV from the official register page and pass its URL/path.
"""
from django.core.management.base import BaseCommand
from study_match.sync import sync_ukvi_sponsors


class Command(BaseCommand):
    help = "Match the GOV.UK student sponsor register to universities."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="URL to the GOV.UK student sponsor register CSV")

    def handle(self, *args, **opts):
        log = sync_ukvi_sponsors(url=opts["url"])
        self.stdout.write(self.style.SUCCESS(
            f"UKVI sync {log.status}: {log.updated_records} matched of {log.total_records} rows."
            + (f" Error: {log.error_message}" if log.error_message else "")
        ))
