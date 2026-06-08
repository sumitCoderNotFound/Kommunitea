"""Import verified course records from a CSV file.

Usage: python manage.py import_courses_csv --file courses.csv
Columns: course_name, university_id (or university_name), degree_level, subject_area,
duration, study_mode, intake_months (semicolon-separated), international_fee_gbp,
ielts_overall, entry_requirements, course_url, source_url.
"""
from django.core.management.base import BaseCommand, CommandError
from study_match.sync import import_courses_csv


class Command(BaseCommand):
    help = "Import course records from a CSV file (free/manual data)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the CSV file")

    def handle(self, *args, **opts):
        try:
            with open(opts["file"], encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            raise CommandError(str(e))
        log = import_courses_csv(text)
        self.stdout.write(self.style.SUCCESS(
            f"Course import {log.status}: +{log.inserted_records} / ~{log.updated_records}, failed {log.failed_records}."
        ))
