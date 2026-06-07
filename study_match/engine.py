"""Rule-based Study Match scoring (Phase 1). No AI required.

Every score is explained in plain language: why it fits, what to watch, next step.
Country score weights (out of 100): academic 25, budget 20, career 20,
visa/post-study 15, city affordability 10, community 10.
"""
from .data import COUNTRIES, UK_CITIES, COURSES, DISCLAIMERS, OFFICIAL_SOURCES

PRIORITY_LABELS = {
    "low_cost": "Low cost", "high_ranking": "High ranking", "easy_city_life": "Easy city life",
    "strong_job_market": "Strong job market", "post_study_work": "Post-study work route",
    "pr_settlement": "PR/settlement pathway", "part_time_jobs": "Part-time jobs",
    "scholarship_chances": "Scholarship chances", "community": "Indian/student community",
    "tech_ecosystem": "Tech/career ecosystem", "safe_accommodation": "Safe accommodation",
    "lower_visa_risk": "Lower visa risk",
}

# Shared 1-5 band → label maps (index 0 unused).
COST_LABELS = ["", "Low", "Affordable", "Average", "High", "Very high"]
PART_TIME_LABELS = ["", "Limited", "Some", "Fair", "Good", "Plenty"]
MARKET_LABELS = ["", "Small", "Modest", "Fair", "Strong", "Very strong"]
ACCOMMODATION_LABELS = ["", "Easy", "Easy", "Moderate", "Hard", "Very hard"]
COMMUNITY_LABELS = ["", "Small", "Some", "Good", "Strong", "Very strong"]
STUDENT_LIFE_LABELS = ["", "Quiet", "Okay", "Good", "Great", "Buzzing"]


def _b(band, invert=False):
    """Normalise a 1-5 band to 0..1 (invert for 'lower is better' like cost)."""
    v = (band - 1) / 4
    return 1 - v if invert else v


def match_course_key(subject: str) -> str | None:
    if not subject:
        return None
    s = subject.lower()
    for key in COURSES:
        if key.lower() in s or s in key.lower():
            return key
    # keyword fallbacks
    for key, c in COURSES.items():
        if any(tok in s for tok in c["background"]):
            return key
    if "comput" in s or "software" in s:
        return "Computer Science"
    if "data" in s:
        return "Data Science"
    if "business" in s or "management" in s:
        return "Business Analytics"
    if "nurs" in s or "health" in s:
        return "Nursing / Healthcare"
    return None


def _budget_sensitive(profile) -> bool:
    return bool(profile.needs_scholarship or "low_cost" in (profile.priorities or [])
                or "scholarship_chances" in (profile.priorities or []))


def score_country(key: str, profile, course_key: str | None):
    c = COUNTRIES[key]
    prios = profile.priorities or []
    budget_sensitive = _budget_sensitive(profile)

    # Academic fit (25): does the country suit the chosen course?
    academic = 0.6
    if course_key and course_key in c.get("best_for", []):
        academic = 1.0
    elif course_key:
        academic = 0.7
    if "high_ranking" in prios and key in ("UK", "USA"):
        academic = min(1.0, academic + 0.1)

    # Budget fit (20): lower tuition/living better if budget-sensitive
    budget = (_b(c["tuition_band"], invert=True) * 0.6 + _b(c["living_band"], invert=True) * 0.4)
    if not budget_sensitive:
        budget = 0.5 + budget * 0.5  # less weight on cost when not budget-driven

    # Career / job market (20)
    career = _b(c["job_market"])
    if "tech_ecosystem" in prios and course_key in ("Computer Science", "Data Science", "Artificial Intelligence"):
        career = min(1.0, career + 0.1)

    # Visa / post-study (15)
    visa = _b(c["post_study_strength"]) * 0.6 + _b(c["visa_difficulty"], invert=True) * 0.4
    if "pr_settlement" in prios and key in ("Canada", "Australia"):
        visa = min(1.0, visa + 0.15)
    if "post_study_work" in prios:
        visa = min(1.0, visa + 0.05)

    # City affordability (10) — use best (cheapest) UK city as proxy for UK; band for others
    city_aff = _b(c["living_band"], invert=True)

    # Community/support (10)
    community = _b(c["community"])
    if "community" in prios and c["community"] >= 4:
        community = min(1.0, community + 0.1)

    total = round(academic * 25 + budget * 20 + career * 20 + visa * 15 + city_aff * 10 + community * 10)
    total = max(0, min(100, total))

    why, risks = [], []
    if academic >= 0.9:
        why.append(f"{c['name']} is a strong fit for {course_key}.")
    if budget >= 0.7:
        why.append("Tuition and living costs are relatively manageable here.")
    elif c["tuition_band"] >= 4:
        risks.append("Tuition and living costs are on the higher side.")
    if c["post_study_strength"] >= 4:
        why.append(f"Good post-study work option: {c['post_study']}.")
    if c["visa_difficulty"] >= 4:
        risks.append("Visa/settlement can be more uncertain here.")
    if c["language_barrier"] >= 3:
        risks.append("Local language may matter for daily life and some jobs.")
    if c["community"] >= 4:
        why.append("Large international/Indian student community for support.")

    return {
        "country": key, "name": c["name"], "score": total,
        "breakdown": {
            "academic_fit": round(academic * 25), "budget_fit": round(budget * 20),
            "career_job_market": round(career * 20), "visa_post_study": round(visa * 15),
            "city_affordability": round(city_aff * 10), "community_support": round(community * 10),
        },
        "why_it_fits": why or [c["summary"]],
        "risks": risks or ["Always confirm current costs and rules from official sources."],
        "visa_notes": c["post_study"], "settlement": c["settlement"],
        "cost_level": ["", "Low", "Below average", "Average", "High", "Very high"][c["tuition_band"]],
        "job_market_strength": ["", "Low", "Below average", "Average", "Strong", "Very strong"][c["job_market"]],
        "official": c["official"],
    }


def recommend_countries(profile, course_key):
    keys = profile.preferred_countries or list(COUNTRIES.keys())
    keys = [k for k in keys if k in COUNTRIES] or list(COUNTRIES.keys())
    scored = [score_country(k, profile, course_key) for k in keys]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def recommend_courses(profile, course_key):
    out = []
    bg = (profile.current_qualification or "").lower()
    goal = (profile.career_goal or "").lower()
    candidates = [course_key] if course_key else []
    for k in COURSES:
        if k not in candidates:
            candidates.append(k)
    for k in candidates[:6]:
        c = COURSES[k]
        fit = 0.5
        if any(tok in bg for tok in c["background"]):
            fit += 0.3
        if any(role.lower() in goal for role in c["roles"]) or any(w in goal for w in k.lower().split()):
            fit += 0.2
        out.append({
            "course": k, "score": min(100, round(fit * 100)),
            "why_it_fits": f"Matches your background/goal and has a {['', 'low', 'modest', 'fair', 'strong', 'very strong'][c['job_signal']]} UK job signal.",
            "skills_needed": c["skills"], "career_roles": c["roles"],
            "job_market_signal": ["", "Low", "Modest", "Fair", "Strong", "Very strong"][c["job_signal"]],
            "sponsor_possibility": ["", "Low", "Low", "Moderate", "Likely", "Strong"][c["sponsor_likely"]],
            "recommended_cities": c["cities"], "communities": c["communities"],
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:4]


def _university_rec(u, city, profile, course_key):
    """Build a detailed, honest university recommendation.

    Curated *signals* (city cost, job market, community, etc.) come from our data.
    Authoritative facts (exact fee, entry requirements, duration, intake) are NOT
    invented — they read "Check official course page" with a source label + link.
    """
    info = UK_CITIES[city]
    course = COURSES.get(course_key) if course_key else None
    city_score = score_city(city, profile)["score"]
    course_signal = course["job_signal"] if course else 3
    match = max(0, min(100, round(0.6 * city_score + 0.4 * (course_signal / 5 * 100))))
    level = profile.desired_study_level or "Masters"
    subject = course_key or profile.subject_interest or "your subject"
    official = f"https://www.google.com/search?q={u.replace(' ', '+')}+{subject.replace(' ', '+')}+{level.replace(' ', '+')}+course"

    why = (f"Strong fit for {subject} in {city} — "
           f"{'affordable' if info['cost'] <= 2 else 'average cost' if info['cost'] == 3 else 'higher cost'}, "
           f"{COMMUNITY_LABELS[info['community']].lower()} community and "
           f"{MARKET_LABELS[info['grad_market']].lower()} graduate job market.")

    return {
        "university": u,
        "course": subject if subject != "your subject" else "Your subject",
        "city": city, "country": "UK", "study_level": level,
        "duration": "Check official course page",
        "intake": profile.preferred_intake or "Check official course page",
        "fee_range": "Check official course page",
        "entry_summary": "Usually a relevant bachelor's degree — confirm exact grades on the official page.",
        "english_requirement": "Usually IELTS/PTE required — check the official page for the exact score.",
        "official_url": official,
        "match_score": match,
        "city_cost_level": COST_LABELS[info["cost"]],
        "part_time_opportunity": PART_TIME_LABELS[info["part_time"]],
        "career_market_signal": MARKET_LABELS[info["grad_market"]],
        "accommodation_difficulty": ACCOMMODATION_LABELS[info["accommodation_difficulty"]],
        "community_signal": COMMUNITY_LABELS[info["community"]],
        "why_it_fits": why,
        "what_to_check": "Confirm exact fees, entry requirements, English score, intake dates and course duration on the official course page.",
        "source_name": "Official university course page",
        "source_url": official,
        "last_checked_at": None,
    }


def recommend_universities(profile, course_key):
    """Suggest UK universities from the best-fit cities for the course (rich shape)."""
    course = COURSES.get(course_key) if course_key else None
    cities = (course["cities"] if course else []) + ["London", "Manchester", "Birmingham"]
    seen, unis = set(), []
    for city in cities:
        info = UK_CITIES.get(city)
        if not info:
            continue
        for u in info["universities"][:2]:
            if u in seen:
                continue
            seen.add(u)
            unis.append(_university_rec(u, city, profile, course_key))
        if len(unis) >= 6:
            break
    unis.sort(key=lambda x: x["match_score"], reverse=True)
    return unis[:6]


def score_city(name, profile):
    info = UK_CITIES[name]
    prios = profile.priorities or []
    budget_sensitive = _budget_sensitive(profile)
    affordability = _b(info["cost"], invert=True)
    score = (affordability * (0.35 if budget_sensitive else 0.2)
             + _b(info["part_time"]) * 0.15 + _b(info["grad_market"]) * 0.2
             + _b(info["student_life"]) * 0.15 + _b(info["community"]) * 0.15)
    if "low_cost" in prios:
        score += affordability * 0.1
    return {
        "city": name, "score": min(100, round(score * 100)),
        "cost_level": ["", "Low", "Affordable", "Average", "High", "Very high"][info["cost"]],
        "student_life": ["", "Quiet", "Okay", "Good", "Great", "Buzzing"][info["student_life"]],
        "part_time_opportunity": ["", "Limited", "Some", "Fair", "Good", "Plenty"][info["part_time"]],
        "career_market": ["", "Small", "Modest", "Fair", "Strong", "Very strong"][info["grad_market"]],
        "accommodation_difficulty": ["", "Easy", "Easy", "Moderate", "Hard", "Very hard"][info["accommodation_difficulty"]],
        "community": ["", "Small", "Some", "Good", "Strong", "Very strong"][info["community"]],
        "best_for": info["best_for"], "universities": info["universities"],
    }


def recommend_cities(profile):
    scored = [score_city(c, profile) for c in UK_CITIES]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:6]


def career_insights(profile, course_key, jobs_provider=None):
    course = COURSES.get(course_key) if course_key else None
    roles = course["roles"] if course else ["Graduate roles in your field"]
    insight = {
        "possible_roles": roles,
        "skills_to_build": course["skills"] if course else ["Communication", "Domain skills"],
        "sponsor_visibility": (course and ["", "Low", "Low", "Moderate", "Likely", "Strong"][course["sponsor_likely"]]) or "Varies",
        "job_market_signal": (course and ["", "Low", "Modest", "Fair", "Strong", "Very strong"][course["job_signal"]]) or "Varies",
        "sponsored_job_finder_link": "/plan/sponsorship-jobs",
        "live_jobs": [],
    }
    # Phase 2: real listings if a jobs provider is configured.
    if jobs_provider and jobs_provider.is_configured and roles:
        insight["live_jobs"] = jobs_provider.search(roles[0], "uk")
    return insight


def visa_cost_checklist():
    return {
        "student_visa": "You'll usually need a confirmed offer (CAS), proof of funds and an approved English test.",
        "graduate_visa": "The Graduate Route lets eligible students stay 2 years (3 for PhD) to work after study.",
        "financial_proof": "Plan for tuition + living costs (often held for 28 days before applying).",
        "official_links": [s for s in OFFICIAL_SOURCES if s["type"] in ("visa", "guidance")],
        "disclaimer": DISCLAIMERS["visa"],
    }


def action_plan(profile):
    return {
        "this_week": [
            "Shortlist 5 universities", "Check the English requirement for your course",
            "Estimate your tuition + living budget", "Join the UK Starter Guide community", "Save 3 courses you like",
        ],
        "this_month": [
            "Prepare your SOP (statement of purpose)", "Gather your documents (transcripts, passport, references)",
            "Apply to your shortlisted universities", "Start accommodation research for your target city",
        ],
    }


def overall_summary(profile, countries, course_key):
    top = countries[0] if countries else None
    course = course_key or (profile.subject_interest or "your chosen subject")
    if top and top["country"] == "UK":
        return (f"Based on your profile, the UK is a strong option to research for {course}, "
                f"especially outside London where cost is lower and tech/career communities are active.")
    if top:
        return (f"Based on your profile, {top['name']} scores highest to research for {course} — "
                f"see the scores below for why, and compare it against the UK.")
    return "Tell us a bit more and we'll suggest the best-fit options to research."


def generate_result(profile, jobs_provider=None):
    course_key = match_course_key(profile.subject_interest or profile.career_goal or "")
    countries = recommend_countries(profile, course_key)
    return {
        "overall_summary": overall_summary(profile, countries, course_key),
        "country_scores": countries,
        "course_recommendations": recommend_courses(profile, course_key),
        "university_recommendations": recommend_universities(profile, course_key),
        "city_recommendations": recommend_cities(profile),
        "career_market_insights": career_insights(profile, course_key, jobs_provider),
        "visa_cost_checklist": visa_cost_checklist(),
        "action_plan": action_plan(profile),
        "disclaimers": DISCLAIMERS,
    }
