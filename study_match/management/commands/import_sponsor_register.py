"""Import EVERY sponsor from the GOV.UK student register as a University.

Max coverage (universities, colleges, language schools). Adds on top of existing
universities; preserves Russell Group flags. Nothing invented.

Usage:
  python manage.py import_sponsor_register --url "<GOV.UK student sponsor register CSV URL>"
"""
from django.core.management.base import BaseCommand
from study_match.sync import import_sponsor_register


class Command(BaseCommand):
    help = "Create a University for every GOV.UK student sponsor (max coverage)."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="URL to the GOV.UK student sponsor register CSV")

    def handle(self, *args, **opts):
        log = import_sponsor_register(url=opts["url"])
        self.stdout.write(self.style.SUCCESS(
            f"Register import {log.status}: +{log.inserted_records} new, ~{log.updated_records} updated, "
            f"{log.failed_records} skipped of {log.total_records} rows."
            + (f" Error: {log.error_message}" if log.error_message else "")
        ))
