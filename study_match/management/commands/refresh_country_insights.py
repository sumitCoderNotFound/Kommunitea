"""Refresh CountryStudyInsight from curated country data.

Scores are DERIVED indicative signals (0–100) from curated bands — clearly not
official statistics. Idempotent; logs a StudyDataImportRun; transaction-safe so a
failure never wipes existing data.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from study_match.models import CountryStudyInsight, StudyDataImportRun
from study_match.data import COUNTRIES

BAND_LABEL = {1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"}

# Major student cities per country (verifiable facts; UK uses curated list).
POPULAR_CITIES = {
    "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Ottawa"],
    "Germany": ["Berlin", "Munich", "Frankfurt", "Aachen"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth"],
    "Ireland": ["Dublin", "Cork", "Galway", "Limerick"],
    "USA": ["New York", "Boston", "San Francisco", "Chicago"],
    "New Zealand": ["Auckland", "Wellington", "Christchurch"],
}


def _pct(value, lo=1, hi=5):
    """Map a 1–5 band to 0–100 (higher band = higher value)."""
    return round((value - lo) / (hi - lo) * 100)


def derive(code, c):
    budget = round(100 - (_pct(c["tuition_band"]) * 0.5 + _pct(c["living_band"]) * 0.5))
    work = round((c["post_study_strength"] + c["job_market"]) / 10 * 100)
    visa = 100 - _pct(c["visa_difficulty"])
    language = 100 - _pct(c["language_barrier"])
    student_life = _pct(c["community"])
    ranking = _pct(c["job_market"])  # reputation proxy (indicative)
    study = round(ranking * 0.5 + student_life * 0.5)
    overall = round(study * 0.2 + work * 0.2 + budget * 0.2 + visa * 0.15 + language * 0.1 + student_life * 0.15)

    risks = []
    if c["living_band"] >= 4:
        risks.append("High living/accommodation costs — budget carefully.")
    if c["visa_difficulty"] >= 4:
        risks.append("Visa/work pathway can be uncertain — check official rules.")
    if c["language_barrier"] >= 3:
        risks.append("Local language helps for daily life and jobs.")
    if not risks:
        risks.append("Confirm current visa, fee and work rules on the official source.")

    return {
        "name": c["name"], "study_score": study, "work_score": work, "budget_score": max(0, budget),
        "visa_score": visa, "language_score": language, "ranking_score": ranking,
        "student_life_score": student_life, "overall_score": overall,
        "best_for_subjects": c.get("best_for", []), "popular_cities": POPULAR_CITIES.get(code, []),
        "tuition_band": BAND_LABEL.get(c["tuition_band"], ""), "living_cost_band": BAND_LABEL.get(c["living_band"], ""),
        "post_study_work_summary": c.get("post_study", ""), "part_time_work_summary": c.get("part_time", ""),
        "language_notes": "English-speaking" if c["language_barrier"] == 1 else "Local language useful for work/daily life",
        "risk_notes": " ".join(risks),
        "weekly_update_summary": f"{c.get('summary', '')} Indicative guidance — always confirm the latest visa, fee and work rules on the official source.",
        "source_name": "Curated (Kommunitea) + official immigration source",
        "source_url": c.get("official", ""), "last_checked_at": timezone.now(), "update_frequency": "monthly",
    }


class Command(BaseCommand):
    help = "Refresh CountryStudyInsight (derived indicative scores) for all curated countries."

    def handle(self, *args, **opts):
        run = StudyDataImportRun.objects.create(source_name="country_insights")
        created = updated = failed = 0
        try:
            with transaction.atomic():
                for code, c in COUNTRIES.items():
                    try:
                        _, made = CountryStudyInsight.objects.update_or_create(country=code, defaults=derive(code, c))
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
            f"Country insights {run.status}: +{created} new, ~{updated} updated, {failed} failed."
        ))
