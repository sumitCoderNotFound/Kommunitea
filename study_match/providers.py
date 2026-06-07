"""Phase 2 external-data adapters with graceful degradation.

Until API keys are configured, providers report is_configured=False and the
engine falls back to curated signals. Set the env vars to switch them on.
"""
import logging

from django.conf import settings

logger = logging.getLogger("kommunitea.studymatch")


class NullJobsProvider:
    is_configured = False

    def search(self, role: str, location: str = "uk"):
        return []


class AdzunaJobsProvider:
    """Live UK job-market signal via Adzuna. Configure ADZUNA_APP_ID + ADZUNA_APP_KEY."""

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, "ADZUNA_APP_ID", "") and getattr(settings, "ADZUNA_APP_KEY", ""))

    def search(self, role: str, location: str = "gb"):
        if not self.is_configured:
            return []
        try:
            import requests
            url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
            resp = requests.get(url, params={
                "app_id": settings.ADZUNA_APP_ID, "app_key": settings.ADZUNA_APP_KEY,
                "what": role, "results_per_page": 5, "content-type": "application/json",
            }, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            return [{
                "title": j.get("title", ""), "company": (j.get("company") or {}).get("display_name", ""),
                "location": (j.get("location") or {}).get("display_name", ""),
                "salary_min": j.get("salary_min"), "url": j.get("redirect_url", ""),
            } for j in data.get("results", [])[:5]]
        except Exception:
            logger.exception("Adzuna search failed")
            return []


def get_jobs_provider():
    p = AdzunaJobsProvider()
    return p if p.is_configured else NullJobsProvider()


class SponsorRegisterProvider:
    """GOV.UK licensed-sponsor lookup. Never *guarantees* sponsorship for a role."""

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, "SPONSOR_REGISTER_URL", ""))

    def is_listed(self, company: str) -> bool | None:
        # Phase 2: load/refresh the official CSV and check membership.
        # Returns None when not configured (UI should say "check official register").
        if not self.is_configured:
            return None
        return None
