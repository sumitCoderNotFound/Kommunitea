"""Sync services for FREE public data. No Apify, no paid APIs.

- sync_universities(url): upsert providers from a public CSV (UKRLP/OfS/data.ac.uk export).
- sync_ukvi_sponsors(url): match GOV.UK student sponsor register to universities.
- import_courses_csv(text): admin CSV upload of verified course records.

Each writes a SyncLog. Network fetches happen on the server at run time; nothing
is invented — unmatched/unknown values stay NULL and needs_verification stays True.
"""
import csv
import io
import re

from django.utils import timezone
from django.utils.text import slugify

from .models import University, Course, SyncLog, DataConfidence, SponsorStatus


def _norm(name: str) -> str:
    """Light normalisation that KEEPS distinguishing words (london, college, etc.).

    Only strips a leading 'the', collapses '&'/'and', and removes punctuation —
    so 'The University of Manchester' and 'University of Manchester' match, but
    'University College London' does NOT collapse to an empty string.
    """
    n = (name or "").lower().strip()
    n = n.replace("&", "and")
    n = re.sub(r"^the\s+", "", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return n


def _fetch(url: str) -> str:
    import requests
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def sync_universities(url: str | None = None) -> SyncLog:
    log = SyncLog.objects.create(source_name="providers", status="running")
    try:
        if not url:
            log.status = "skipped"; log.error_message = "No source URL provided."; log.finished_at = timezone.now(); log.save()
            return log
        rows = list(csv.DictReader(io.StringIO(_fetch(url))))
        ins = upd = fail = 0
        for r in rows:
            name = (r.get("name") or r.get("Provider Name") or r.get("PROVIDER_NAME") or "").strip()
            if not name:
                fail += 1
                continue
            slug = slugify(name)[:120]
            defaults = {
                "university_name": name,
                "website_url": (r.get("website") or r.get("Website") or "").strip(),
                "ukprn": (r.get("ukprn") or r.get("UKPRN") or "").strip(),
                "postcode": (r.get("postcode") or r.get("Postcode") or "").strip(),
                "city": (r.get("city") or r.get("Town") or "").strip(),
                "source_url": url, "last_checked_at": timezone.now(),
            }
            obj, created = University.objects.update_or_create(university_id=slug, defaults=defaults)
            ins += 1 if created else 0
            upd += 0 if created else 1
        log.total_records, log.inserted_records, log.updated_records, log.failed_records = len(rows), ins, upd, fail
        log.status = "success"
    except Exception as e:
        log.status = "failed"; log.error_message = str(e)[:500]
    log.finished_at = timezone.now(); log.save()
    return log


def sync_ukvi_sponsors(url: str | None = None) -> SyncLog:
    """Match the GOV.UK student sponsor register to existing universities.

    Handles the register's leading title rows, matches each UNIVERSITY against the
    register (exact normalised name, then containment), and reports the number of
    universities actually updated (not raw register rows).
    """
    log = SyncLog.objects.create(source_name="ukvi_sponsors", status="running")
    try:
        if not url:
            log.status = "skipped"; log.error_message = "No register URL provided."; log.finished_at = timezone.now(); log.save()
            return log

        raw = _fetch(url)
        lines = raw.splitlines()
        # GOV.UK puts a few title rows before the real header — find the header line.
        start = 0
        for i, line in enumerate(lines[:15]):
            low = line.lower()
            if "sponsor name" in low or "organisation name" in low or ("organisation" in low and "rating" in low):
                start = i
                break
        reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))

        def col(row, *names):
            for n in names:
                for k, v in row.items():
                    if k and k.strip().lower() == n.lower():
                        return (v or "").strip()
            return ""

        # Build a register index: normalised org name -> rating/status.
        register = {}
        total = 0
        for row in reader:
            total += 1
            org = col(row, "Sponsor Name", "Organisation Name", "Organisation", "Name")
            if not org:
                continue
            register[_norm(org)] = col(row, "Status", "Type & Rating", "Type and Rating", "Sponsor Type", "Rating")

        STOP = {"the", "of", "at", "and", "in", "for"}
        def tokens(s):
            return {t for t in s.split() if t not in STOP}
        reg_tokens = {k: tokens(k) for k in register}
        reg_keys = list(register.keys())

        matched = 0
        for uni in University.objects.all():
            key = _norm(uni.university_name)
            rating = register.get(key)
            if rating is None:
                # 1) containment, then 2) token-set subset (handles reordered legal names
                #    e.g. "Durham University" vs "University of Durham").
                hit = next((rk for rk in reg_keys if key and len(key) > 8 and (key in rk or rk in key)), None)
                if not hit:
                    ut = tokens(key)
                    hit = next((rk for rk in reg_keys if len(ut) >= 2 and (ut <= reg_tokens[rk] or reg_tokens[rk] <= ut)), None)
                rating = register.get(hit) if hit else None
            if rating is not None:
                uni.ukvi_sponsor_status = SponsorStatus.LICENSED
                uni.sponsor_rating = (rating or "")[:40]
                uni.needs_verification = False
                if uni.data_confidence == DataConfidence.LOW:
                    uni.data_confidence = DataConfidence.MEDIUM
                uni.last_checked_at = timezone.now()
                uni.save(update_fields=["ukvi_sponsor_status", "sponsor_rating", "needs_verification", "data_confidence", "last_checked_at"])
                matched += 1

        log.total_records = total
        log.updated_records = matched  # universities updated, not register rows
        log.status = "success"
    except Exception as e:
        log.status = "failed"; log.error_message = str(e)[:500]
    log.finished_at = timezone.now(); log.save()
    return log


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "").replace("£", "").strip()))
    except (ValueError, TypeError):
        return None


def import_courses_csv(text: str) -> SyncLog:
    """Admin CSV import. Columns: course_name, university_id or university_name,
    degree_level, subject_area, duration, study_mode, intake_months, international_fee_gbp,
    ielts_overall, entry_requirements, course_url, source_url. Unknown values stay NULL.
    """
    log = SyncLog.objects.create(source_name="courses_csv", status="running")
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
        ins = upd = fail = 0
        for r in rows:
            name = (r.get("course_name") or "").strip()
            uni = None
            if r.get("university_id"):
                uni = University.objects.filter(university_id=r["university_id"].strip()).first()
            if not uni and r.get("university_name"):
                uni = University.objects.filter(university_name__iexact=r["university_name"].strip()).first()
            if not name or not uni:
                fail += 1
                continue
            slug = slugify(f"{uni.university_id}-{name}")[:160]
            intakes = [m.strip() for m in (r.get("intake_months") or "").split(";") if m.strip()]
            defaults = {
                "university": uni, "university_name": uni.university_name, "course_name": name,
                "degree_level": (r.get("degree_level") or "").strip(),
                "subject_area": (r.get("subject_area") or "").strip(),
                "duration": (r.get("duration") or "").strip(),
                "study_mode": (r.get("study_mode") or "").strip(),
                "intake_months": intakes,
                "international_fee_gbp": _to_int(r.get("international_fee_gbp")),
                "ielts_overall": (r.get("ielts_overall") or None),
                "entry_requirements": (r.get("entry_requirements") or "").strip(),
                "english_language_requirement": (r.get("english_language_requirement") or "").strip(),
                "course_url": (r.get("course_url") or "").strip(),
                "application_url": (r.get("application_url") or "").strip(),
                "source_url": (r.get("source_url") or r.get("course_url") or "").strip(),
                "fee_verified": False, "needs_verification": True,
                "data_confidence": DataConfidence.MEDIUM if r.get("source_url") else DataConfidence.LOW,
                "last_checked_at": timezone.now(),
            }
            _, created = Course.objects.update_or_create(course_id=slug, defaults=defaults)
            ins += 1 if created else 0
            upd += 0 if created else 1
        log.total_records, log.inserted_records, log.updated_records, log.failed_records = len(rows), ins, upd, fail
        log.status = "success"
    except Exception as e:
        log.status = "failed"; log.error_message = str(e)[:500]
    log.finished_at = timezone.now(); log.save()
    return log
