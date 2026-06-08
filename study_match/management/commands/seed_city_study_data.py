"""Seed/refresh CityStudyData for the 25 UK cities (curated indicative signals).

Top universities are derived FACTUALLY from the live University catalog (matched
by city). Signals are curated indicative bands; monthly cost is a band, never a
precise figure. Logs a StudyDataImportRun; transaction-safe.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from study_match.models import CityStudyData, University, StudyDataImportRun, DataConfidence
from study_match.city_data import (
    CITY_DATA, COST_LABEL, COST_BAND, RENT_LABEL, SIGNAL_4, ACCOM_LABEL,
    SOURCE_NAME, SOURCE_URL, city_match_score,
)


class Command(BaseCommand):
    help = "Seed/refresh the 25 UK cities with curated indicative signals + real universities."

    def handle(self, *args, **opts):
        run = StudyDataImportRun.objects.create(source_name="city_study_data")
        created = updated = failed = 0
        try:
            with transaction.atomic():
                for city, (region, cost, rent, pt, grad, life, comm, accom, best_for, industries) in CITY_DATA.items():
                    try:
                        unis = list(
                            University.objects.filter(city__iexact=city).order_by("-is_russell_group", "university_name")
                            .values_list("university_name", flat=True)[:6]
                        )
                        score, _ = city_match_score(cost, rent, pt, grad, life, comm, accom)
                        cautions = []
                        if cost >= 4:
                            cautions.append("Higher living costs — budget carefully.")
                        if accom >= 4:
                            cautions.append("Accommodation is competitive — start searching early.")
                        if comm <= 2:
                            cautions.append("Smaller international community than major hubs.")
                        if not cautions:
                            cautions.append("Confirm current rent and living costs before deciding.")

                        defaults = {
                            "city": city, "region": region, "country": "United Kingdom",
                            "cost_level": COST_LABEL[cost], "rent_level": RENT_LABEL[rent],
                            "monthly_living_cost_band": COST_BAND[cost], "average_rent_band": COST_BAND[rent],
                            "part_time_job_signal": SIGNAL_4[pt], "graduate_job_market_signal": SIGNAL_4[grad],
                            "student_life_signal": SIGNAL_4[life], "international_community_signal": SIGNAL_4[comm],
                            "accommodation_difficulty": ACCOM_LABEL[accom],
                            "main_industries": industries, "best_for_subjects": best_for,
                            "best_for_career_areas": industries, "top_universities": unis,
                            "city_summary": f"{city} — strong for {', '.join(best_for[:2])}; "
                                            f"{SIGNAL_4[life].lower()} student life and {SIGNAL_4[comm].lower()} "
                                            f"international community. {COST_LABEL[cost]} living costs.",
                            "why_choose_this_city": f"Good for {', '.join(best_for)}. "
                                                    f"Part-time jobs: {SIGNAL_4[pt]}; graduate market: {SIGNAL_4[grad]}.",
                            "what_to_be_careful_about": " ".join(cautions),
                            "cost_value": cost, "rent_value": rent, "part_time_value": pt, "grad_value": grad,
                            "student_life_value": life, "community_value": comm, "accommodation_value": accom,
                            "overall_city_score": score,
                            "source_name": SOURCE_NAME, "source_url": SOURCE_URL,
                            "data_confidence": DataConfidence.LOW,  # curated/indicative
                            "last_checked_at": timezone.now(),
                        }
                        _, made = CityStudyData.objects.update_or_create(slug=slugify(city), defaults=defaults)
                        created += 1 if made else 0
                        updated += 0 if made else 1
                    except Exception:
                        failed += 1
            run.status = "success"
        except Exception as e:
            run.status = "failed"; run.error_message = str(e)[:500]
        run.records_created, run.records_updated, run.records_failed = created, updated, failed
        run.finished_at = timezone.now(); run.save()
        self.stdout.write(self.style.SUCCESS(
            f"City data {run.status}: +{created} new, ~{updated} updated, {failed} failed."
        ))
