"""StudyMatch course scoring against the real catalog (free-data driven).

Weights (out of 100): course 25, budget 20, ranking 10, location 10,
visa sponsor 15, entry 10, english 5, scholarship/placement 5.

Rules:
- Not-licensed (or unknown) sponsor → warning (caller may exclude).
- Missing fee → no FULL budget score + warning.
- Low data confidence → warning. Never invent missing values.
"""
from decimal import Decimal

WEIGHTS = {
    "course_match": 25, "budget_match": 20, "ranking_reputation": 10, "location_preference": 10,
    "visa_sponsor": 15, "entry_requirement": 10, "english_requirement": 5, "scholarship_placement": 5,
}


def _subject_match(course, desired: str) -> float:
    if not desired:
        return 0.6
    d = desired.lower()
    hay = f"{course.course_name} {course.subject_area} {course.degree_level}".lower()
    if d in hay or any(tok in hay for tok in d.split() if len(tok) > 2):
        return 1.0
    return 0.3


def score_course(course, params: dict) -> dict:
    uni = course.university
    reasons, warnings = [], []
    b = {}

    # Course match (25)
    cm = _subject_match(course, params.get("desired_subject", ""))
    b["course_match"] = round(cm * WEIGHTS["course_match"])
    if cm >= 1.0:
        reasons.append(f"Matches your interest in {params.get('desired_subject') or 'this subject'}.")

    # Budget (20) — never full credit when the fee is unknown.
    budget = params.get("budget_gbp")
    if course.international_fee_gbp is None:
        b["budget_match"] = round(0.4 * WEIGHTS["budget_match"])
        warnings.append("Tuition fee not confirmed yet — budget score is partial. Check the official course page.")
    elif budget:
        fee = course.international_fee_gbp
        if fee <= budget:
            b["budget_match"] = WEIGHTS["budget_match"]
            reasons.append("Fits within your stated budget.")
        elif fee <= budget * 1.15:
            b["budget_match"] = round(0.6 * WEIGHTS["budget_match"])
            warnings.append("Slightly above your budget.")
        else:
            b["budget_match"] = round(0.2 * WEIGHTS["budget_match"])
            warnings.append("Above your budget.")
    else:
        b["budget_match"] = round(0.6 * WEIGHTS["budget_match"])

    # Ranking / reputation (10) — Russell Group as an honest, factual proxy.
    b["ranking_reputation"] = WEIGHTS["ranking_reputation"] if uni.is_russell_group else round(0.6 * WEIGHTS["ranking_reputation"])
    if uni.is_russell_group:
        reasons.append("Russell Group university.")

    # Location (10)
    cities = [c.lower() for c in (params.get("preferred_cities") or [])]
    regions = [r.lower() for r in (params.get("preferred_regions") or [])]
    if not cities and not regions:
        b["location_preference"] = round(0.7 * WEIGHTS["location_preference"])
    elif uni.city.lower() in cities or uni.region.lower() in regions:
        b["location_preference"] = WEIGHTS["location_preference"]
        reasons.append(f"In your preferred location ({uni.city}).")
    else:
        b["location_preference"] = round(0.3 * WEIGHTS["location_preference"])

    # Visa sponsor (15)
    if uni.ukvi_sponsor_status == "licensed":
        b["visa_sponsor"] = WEIGHTS["visa_sponsor"]
        reasons.append("On the UKVI student sponsor register.")
    elif uni.ukvi_sponsor_status == "not_listed":
        b["visa_sponsor"] = 0
        warnings.append("Not currently on the student sponsor register — verify on GOV.UK before applying.")
    else:
        b["visa_sponsor"] = round(0.5 * WEIGHTS["visa_sponsor"])
        warnings.append("Sponsor status not confirmed yet — check the GOV.UK register.")

    # Entry requirement (10) — partial unless we have data to compare.
    if course.entry_requirements:
        b["entry_requirement"] = round(0.7 * WEIGHTS["entry_requirement"])
    else:
        b["entry_requirement"] = round(0.5 * WEIGHTS["entry_requirement"])
        warnings.append("Entry requirements not confirmed — check the official course page.")

    # English (5)
    ielts = params.get("ielts_score")
    if course.ielts_overall is not None and ielts:
        try:
            b["english_requirement"] = WEIGHTS["english_requirement"] if Decimal(str(ielts)) >= course.ielts_overall else 0
            if b["english_requirement"] == 0:
                warnings.append(f"Your IELTS may be below the required {course.ielts_overall}.")
        except Exception:
            b["english_requirement"] = round(0.5 * WEIGHTS["english_requirement"])
    else:
        b["english_requirement"] = round(0.6 * WEIGHTS["english_requirement"])

    # Scholarship / placement (5)
    sp = 0.0
    if params.get("wants_placement") and course.work_placement_available:
        sp += 0.5
    if params.get("needs_scholarship") and course.scholarship_info:
        sp += 0.5
    if not params.get("wants_placement") and not params.get("needs_scholarship"):
        sp = 0.6
    b["scholarship_placement"] = round(sp * WEIGHTS["scholarship_placement"])

    if course.data_confidence == "low" or course.needs_verification:
        warnings.append("Some details are unverified — always confirm on the official source.")

    total = max(0, min(100, sum(b.values())))
    return {
        "match_percentage": total,
        "score_breakdown": b,
        "reasons": reasons,
        "warnings": warnings,
        "source_url": course.source_url or uni.website_url,
        "last_checked_at": course.last_checked_at,
    }


def rank_courses(courses, params: dict, limit: int = 20):
    scored = []
    for c in courses:
        result = score_course(c, params)
        scored.append((c, result))
    scored.sort(key=lambda x: x[1]["match_percentage"], reverse=True)
    return scored[:limit]
