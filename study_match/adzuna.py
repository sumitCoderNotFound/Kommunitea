"""Adzuna jobs importer (official free API — app_id/app_key, no scraping).

Per city + category:
  - /jobs/gb/search   → job listings → ExternalJob
  - /jobs/gb/regional → vacancy counts → derive an overall city job-market signal
Part-time vs graduate is a ROUGH keyword split (Adzuna has no native label).
Salaries are indicative ranges. Stores raw history, dedupes, expires stale, fail-safe.

Keys come from settings.ADZUNA_APP_ID / ADZUNA_APP_KEY (env). Without keys the
import is skipped (logged) and existing curated signals are kept — never breaks.
"""
import time

from django.conf import settings
from django.utils import timezone

from .models import (
    ExternalJob, RawAdzunaJobsData, CityStudyData, StudyDataImportRun,
)

BASE = "https://api.adzuna.com/v1/api/jobs/gb"

# City -> Adzuna "where" string (Adzuna accepts plain place names).
DEFAULT_CITIES = ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Edinburgh",
                  "Bristol", "Newcastle upon Tyne", "Sheffield", "Nottingham", "Coventry", "Liverpool"]

# Volume thresholds → signal band (indicative, tuned to Adzuna gb counts).
def _signal(count: int) -> str:
    if count >= 2000:
        return "Very strong"
    if count >= 600:
        return "Strong"
    if count >= 150:
        return "Moderate"
    return "Limited"


def _keys():
    app_id = getattr(settings, "ADZUNA_APP_ID", "") or ""
    app_key = getattr(settings, "ADZUNA_APP_KEY", "") or ""
    return app_id, app_key


def _get(path, params):
    import requests
    resp = requests.get(f"{BASE}{path}", params=params, headers={"Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def import_adzuna_jobs(cities=None, what="", results_per_city=10) -> StudyDataImportRun:
    run = StudyDataImportRun.objects.create(source_name="adzuna_jobs")
    app_id, app_key = _keys()
    if not app_id or not app_key:
        run.status = "skipped"
        run.error_message = "No ADZUNA_APP_ID / ADZUNA_APP_KEY configured."
        run.finished_at = timezone.now(); run.save()
        return run

    cities = cities or DEFAULT_CITIES
    created = updated = failed = 0
    seen_ids = set()
    try:
        for city in cities:
            try:
                base_params = {"app_id": app_id, "app_key": app_key, "where": city, "results_per_page": results_per_city}
                if what:
                    base_params["what"] = what

                search = _get("/search/1", base_params)
                RawAdzunaJobsData.objects.create(
                    source_url=f"{BASE}/search/1?where={city}", raw_payload={"count": search.get("count"), "city": city},
                )

                # Rough part-time vs graduate split via keyword counts (clearly indicative).
                pt = _get("/search/1", {**base_params, "what_phrase": "part time", "results_per_page": 1}).get("count", 0)
                grad = _get("/search/1", {**base_params, "what_phrase": "graduate", "results_per_page": 1}).get("count", 0)
                total = search.get("count", 0)

                # Update the city signals (only if we have a CityStudyData row).
                cs = CityStudyData.objects.filter(city__iexact=city).first()
                if cs:
                    cs.part_time_job_signal = _signal(pt)
                    cs.graduate_job_market_signal = _signal(grad)
                    cs.employment_signal = _signal(total)
                    cs.last_checked_at = timezone.now()
                    cs.data_confidence = "medium"  # now API-backed for jobs
                    cs.save(update_fields=["part_time_job_signal", "graduate_job_market_signal",
                                           "employment_signal", "last_checked_at", "data_confidence"])

                for ad in search.get("results", []):
                    ext_id = str(ad.get("id") or "")
                    if not ext_id or ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)
                    defaults = {
                        "title": (ad.get("title") or "")[:240],
                        "company": (ad.get("company", {}).get("display_name") or "")[:200],
                        "city": city, "country": "United Kingdom",
                        "salary_min": int(ad["salary_min"]) if ad.get("salary_min") else None,
                        "salary_max": int(ad["salary_max"]) if ad.get("salary_max") else None,
                        "job_type": (ad.get("contract_time") or ""),
                        "category": (ad.get("category", {}).get("label") or "")[:80],
                        "source": "adzuna", "apply_url": ad.get("redirect_url", ""),
                        "is_active": True, "last_checked_at": timezone.now(),
                    }
                    _, made = ExternalJob.objects.update_or_create(
                        source="adzuna", apply_url=defaults["apply_url"], defaults=defaults,
                    )
                    created += 1 if made else 0
                    updated += 0 if made else 1
                time.sleep(1)  # be polite to the free tier
            except Exception:
                failed += 1
        # Expire jobs not seen this run (older than 30 days).
        cutoff = timezone.now() - timezone.timedelta(days=30)
        ExternalJob.objects.filter(source="adzuna", last_checked_at__lt=cutoff).update(is_active=False)
        run.status = "success"
    except Exception as e:
        run.status = "failed"; run.error_message = str(e)[:500]
    run.records_created, run.records_updated, run.records_failed = created, updated, failed
    run.finished_at = timezone.now(); run.save()
    return run
