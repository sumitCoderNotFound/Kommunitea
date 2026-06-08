"""Seed the UK university catalog with verifiable facts only.

Seeds the 24 Russell Group universities + other large international-student
universities (real name/city/region/website). No fees/IELTS/sponsor data is
invented — those stay NULL/unknown with needs_verification=True until the
GOV.UK sponsor sync and admin/CSV verification fill them in.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from study_match.models import University, DataSource, DataConfidence, SponsorStatus
from study_match.catalog_data import RUSSELL_GROUP, OTHER_UNIVERSITIES, OFFICIAL_DATA_SOURCES


class Command(BaseCommand):
    help = "Seed UK universities (facts only) and official data sources."

    def handle(self, *args, **opts):
        now = timezone.now()
        created = updated = 0
        for is_rg, rows in ((True, RUSSELL_GROUP), (False, OTHER_UNIVERSITIES)):
            for name, city, region, website in rows:
                obj, made = University.objects.update_or_create(
                    university_id=slugify(name)[:120],
                    defaults={
                        "university_name": name, "city": city, "region": region,
                        "country": "United Kingdom", "website_url": website,
                        "is_russell_group": is_rg,
                        "ukvi_sponsor_status": SponsorStatus.UNKNOWN,  # filled by GOV.UK sync
                        "source_url": "https://russellgroup.ac.uk/about/our-universities/" if is_rg else website,
                        "data_confidence": DataConfidence.MEDIUM,
                        "needs_verification": True,
                        "last_checked_at": now,
                    },
                )
                created += 1 if made else 0
                updated += 0 if made else 1

        for s in OFFICIAL_DATA_SOURCES:
            DataSource.objects.update_or_create(source_name=s["source_name"], defaults=s)

        self.stdout.write(self.style.SUCCESS(
            f"Catalog seeded: {created} created, {updated} updated, {University.objects.count()} total universities. "
            f"Run 'sync_ukvi_sponsors --url <GOV.UK register CSV>' to fill sponsor status."
        ))
