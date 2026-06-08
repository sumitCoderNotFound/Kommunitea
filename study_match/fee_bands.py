"""Indicative international fee bands (study level + subject group).

These are BROAD, published indicative ranges (British Council Study UK / UKCISA),
shown only as guidance — never as an exact or guaranteed fee. A course's exact fee,
when verified, is shown separately. Bands are classified from a course's degree level
and subject area; nothing here is a per-university fact.
"""

SOURCE = "British Council Study UK / UKCISA — indicative ranges"
SOURCE_URL = "https://study-uk.britishcouncil.org/moving-uk/tuition-fees"

# key -> label + broad indicative GBP/year range
BANDS = {
    "ug_classroom": {"label": "Undergraduate · classroom-based", "min": 11400, "max": 22000},
    "ug_lab":       {"label": "Undergraduate · lab / STEM",       "min": 15000, "max": 30000},
    "ug_clinical":  {"label": "Undergraduate · clinical / medical", "min": 25000, "max": 58000},
    "pg_classroom": {"label": "Postgraduate · classroom-based",   "min": 12000, "max": 24000},
    "pg_lab":       {"label": "Postgraduate · lab / STEM",        "min": 15000, "max": 32000},
    "pg_business":  {"label": "Postgraduate · business / MBA",    "min": 18000, "max": 57000},
    "pg_clinical":  {"label": "Postgraduate · clinical / medical", "min": 25000, "max": 55000},
    "phd":          {"label": "PhD / research",                   "min": 16000, "max": 30000},
}

_CLINICAL = ["medic", "dent", "nurs", "veterin", "clinical", "pharm", "midwif", "health", "physio", "dietet", "optom"]
_BUSINESS = ["business", "management", "mba", "finance", "account", "marketing", "economics"]
_STEM = ["engineer", "comput", "data", "software", "cyber", "science", "physic", "chemist",
         "biolog", "math", "technolog", "artificial intelligence", "robotic", "informatic"]


def _level(degree_level: str) -> str:
    d = (degree_level or "").lower()
    if any(k in d for k in ["phd", "doctor", "dphil", "research degree"]):
        return "phd"
    if any(k in d for k in ["master", "msc", "mba", "llm", "mphil", "pgdip", "pgcert", "postgrad", "pg ", "m.a", "ma "]):
        return "pg"
    return "ug"


def _group(subject: str, level: str) -> str:
    s = (subject or "").lower()
    if any(k in s for k in _CLINICAL):
        return "clinical"
    if level == "pg" and any(k in s for k in _BUSINESS):
        return "business"
    if any(k in s for k in _STEM):
        return "lab"
    return "classroom"


def classify(degree_level: str, subject_area: str) -> str:
    level = _level(degree_level)
    group = _group(subject_area, level)
    if level == "phd":
        return "phd"
    if level == "pg":
        return {"clinical": "pg_clinical", "business": "pg_business", "lab": "pg_lab"}.get(group, "pg_classroom")
    # undergraduate (business UG falls under classroom)
    return {"clinical": "ug_clinical", "lab": "ug_lab"}.get(group, "ug_classroom")


def band_for_course(course) -> dict:
    key = classify(course.degree_level, course.subject_area)
    b = BANDS[key]
    return {"key": key, "label": b["label"], "minGbp": b["min"], "maxGbp": b["max"],
            "source": SOURCE, "sourceUrl": SOURCE_URL}


def all_bands() -> list:
    return [{"key": k, "label": v["label"], "minGbp": v["min"], "maxGbp": v["max"]} for k, v in BANDS.items()]
