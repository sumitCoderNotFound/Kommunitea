"""Import jobs + city job signals from the Adzuna API.

Usage:
  python manage.py import_adzuna_jobs                 # default cities, all categories
  python manage.py import_adzuna_jobs --what "data"   # filter by keyword
Needs ADZUNA_APP_ID / ADZUNA_APP_KEY env vars (free signup at developer.adzuna.com).
"""
from django.core.management.base import BaseCommand
from study_match.adzuna import import_adzuna_jobs


class Command(BaseCommand):
    help = "Import Adzuna jobs and derive city job-market signals."

    def add_arguments(self, parser):
        parser.add_argument("--what", default="", help="Optional keyword filter (e.g. 'data science')")
        parser.add_argument("--cities", default="", help="Comma-separated city list (default: major UK cities)")
        parser.add_argument("--per-city", type=int, default=10, help="Listings to store per city")

    def handle(self, *args, **opts):
        cities = [c.strip() for c in opts["cities"].split(",") if c.strip()] or None
        log = import_adzuna_jobs(cities=cities, what=opts["what"], results_per_city=opts["per_city"])
        self.stdout.write(self.style.SUCCESS(
            f"Adzuna import {log.status}: +{log.records_created} new, ~{log.records_updated} updated, "
            f"{log.records_failed} failed." + (f" {log.error_message}" if log.error_message else "")
        ))
