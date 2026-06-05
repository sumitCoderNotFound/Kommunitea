"""The three AI features, each with an AI path and a non-AI fallback."""
import json
from . import providers


# ---------- 1. AI Profile Builder ----------
def build_profile(data: dict) -> dict:
    name = data.get("full_name") or "this member"
    course = data.get("course") or ""
    university = data.get("university") or ""
    skills = ", ".join(data.get("skills") or [])
    goals = data.get("career_goals") or ""
    status = data.get("status") or ""

    if providers.ai_enabled():
        system = ("You are a warm, professional career writer for a UK student/graduate community. "
                  "Write in first person, friendly but professional, no emojis, 3-4 sentences max.")
        user = (f"Write a short profile bio.\nName: {name}\nCourse: {course}\nUniversity: {university}\n"
                f"Status: {status}\nSkills: {skills}\nGoals: {goals}\n"
                "Also suggest a one-line headline. Return JSON: {\"bio\": \"...\", \"headline\": \"...\"}")
        try:
            raw = providers.complete(system, user, max_tokens=400)
            parsed = _try_json(raw)
            if parsed and "bio" in parsed:
                return {"bio": parsed["bio"], "headline": parsed.get("headline", ""), "aiPowered": True}
            return {"bio": raw.strip(), "headline": "", "aiPowered": True}
        except Exception as e:
            return {**_fallback_profile(name, course, university, skills, goals), "note": f"AI error, used fallback: {e}"}

    return _fallback_profile(name, course, university, skills, goals)


def _fallback_profile(name, course, university, skills, goals):
    parts = []
    if course and university:
        parts.append(f"I'm studying {course} at {university}.")
    elif university:
        parts.append(f"I'm part of the {university} community.")
    if skills:
        parts.append(f"My main skills are {skills}.")
    if goals:
        parts.append(f"Right now I'm focused on {goals.lower()}.")
    parts.append("Always happy to connect, share, and help others in the tribe.")
    headline = (course or "Student").strip() + (f" @ {university}" if university else "")
    return {"bio": " ".join(parts), "headline": headline, "aiPowered": False}


# ---------- 2. AI CV Review ----------
def review_cv(cv_text: str) -> dict:
    cv_text = (cv_text or "").strip()
    if len(cv_text) < 40:
        return {"error": "Please paste at least a few lines of your CV."}

    if providers.ai_enabled():
        system = ("You are an expert UK career coach reviewing a CV for a student/graduate. "
                  "Be specific and constructive.")
        user = (f"Review this CV. Return JSON with arrays: "
                f"{{\"strengths\": [..], \"improvements\": [..], \"atsTips\": [..], \"summary\": \"..\"}}.\n\nCV:\n{cv_text[:6000]}")
        try:
            raw = providers.complete(system, user, max_tokens=800, temperature=0.4)
            parsed = _try_json(raw)
            if parsed:
                parsed["aiPowered"] = True
                return parsed
            return {"summary": raw.strip(), "strengths": [], "improvements": [], "atsTips": [], "aiPowered": True}
        except Exception as e:
            return {**_fallback_cv(cv_text), "note": f"AI error, used fallback: {e}"}

    return _fallback_cv(cv_text)


def _fallback_cv(cv_text: str):
    lower = cv_text.lower()
    strengths, improvements, ats = [], [], []
    words = len(cv_text.split())
    if words > 200: strengths.append("Good level of detail and content length.")
    else: improvements.append("Your CV looks short. Add more detail on projects and impact.")
    if any(c.isdigit() for c in cv_text): strengths.append("You include numbers, which makes achievements concrete.")
    else: improvements.append("Add measurable results (e.g. 'improved X by 20%').")
    action_verbs = ["led", "built", "created", "managed", "designed", "improved", "developed", "delivered"]
    if any(v in lower for v in action_verbs): strengths.append("You use strong action verbs.")
    else: improvements.append("Start bullet points with action verbs (Built, Led, Designed).")
    if "@" in cv_text: strengths.append("Contact details are present.")
    else: improvements.append("Make sure your email and LinkedIn are clearly visible.")
    ats.append("Use a simple, single-column layout so applicant tracking systems can read it.")
    ats.append("Mirror keywords from the job description you are applying to.")
    ats.append("Save and send as PDF unless asked otherwise.")
    return {"summary": "Here is a quick review of your CV.", "strengths": strengths,
            "improvements": improvements, "atsTips": ats, "aiPowered": False}


# ---------- 3. AI Job Matching ----------
def match_jobs(user, jobs: list) -> dict:
    profile = {
        "skills": user.skills or [], "interests": user.interests or [],
        "looking_for": user.looking_for or [], "course": user.course,
        "career_goals": user.career_goals, "city": user.city,
    }
    job_list = [{"id": j.id, "title": j.title, "company": j.company,
                 "location": j.location, "description": (j.description or "")[:400],
                 "category": getattr(j, "category", "")} for j in jobs]

    if not job_list:
        return {"matches": [], "aiPowered": providers.ai_enabled(),
                "note": "No jobs posted yet. Once moderators add jobs, your matches will appear here."}

    if providers.ai_enabled():
        system = "You match UK students/grads to jobs. Be concise and practical."
        user_p = (f"My profile: {json.dumps(profile)}\n\nJobs: {json.dumps(job_list)}\n\n"
                  "Rank the best matches. Return JSON: {\"matches\": [{\"id\": <jobId>, \"score\": 0-100, \"reason\": \"..\"}]}")
        try:
            raw = providers.complete(system, user_p, max_tokens=700, temperature=0.3)
            parsed = _try_json(raw)
            if parsed and "matches" in parsed:
                parsed["aiPowered"] = True
                return parsed
        except Exception:
            pass  # fall through to heuristic

    return _fallback_match(profile, job_list)


def _fallback_match(profile, job_list):
    terms = set()
    for key in ("skills", "interests", "looking_for"):
        terms |= {t.lower() for t in profile.get(key, [])}
    if profile.get("course"): terms |= set(profile["course"].lower().split())
    matches = []
    for j in job_list:
        haystack = f"{j['title']} {j['company']} {j['description']} {j['category']}".lower()
        hits = [t for t in terms if t and t in haystack]
        score = min(100, len(hits) * 20)
        if hits:
            matches.append({"id": j["id"], "score": score,
                            "reason": f"Matches your {', '.join(sorted(set(hits))[:3])}."})
    matches.sort(key=lambda m: m["score"], reverse=True)
    if not matches:  # show some jobs anyway
        matches = [{"id": j["id"], "score": 0, "reason": "Worth a look based on your area."} for j in job_list[:3]]
    return {"matches": matches, "aiPowered": False}


def _try_json(raw: str):
    if not raw: return None
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):] if "{" in raw else raw
    try:
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception:
        return None


# ---------- AI Career Assistant (chat) ----------
def career_assistant_reply(user_message: str, history: list | None = None, profile: dict | None = None) -> str:
    """Generate a reply for the in-app AI Career Assistant chat.
    Falls back to a helpful canned response when no AI provider is configured."""
    user_message = (user_message or "").strip()
    if not user_message:
        return "Ask me anything about your career, CV, interviews, or job search in the UK."

    if providers.ai_enabled():
        system = (
            "You are Kommunitea's AI Career Assistant for UK students, graduates and professionals. "
            "Be warm, concise and practical. Give specific, actionable advice on CVs, interviews, "
            "job applications, visas (PSW/Graduate route), networking and skills. No emojis. "
            "Keep replies under 180 words unless asked for detail."
        )
        ctx = ""
        if profile:
            ctx = (f"\nUser context — name: {profile.get('full_name','')}, course: {profile.get('course','')}, "
                   f"university: {profile.get('university','')}, skills: {', '.join(profile.get('skills') or [])}.")
        convo = ""
        for h in (history or [])[-6:]:
            role = "Assistant" if h.get("is_ai") else "User"
            convo += f"\n{role}: {h.get('body','')}"
        user = f"{ctx}\nConversation so far:{convo}\n\nUser: {user_message}\nAssistant:"
        try:
            return providers.complete(system, user, max_tokens=400, temperature=0.6).strip()
        except Exception:
            pass
    # Non-AI fallback
    return (
        "Here's a quick steer: focus your CV on measurable results, tailor each application to the role, "
        "and prepare 3-4 STAR stories for interviews. For UK roles, highlight your right-to-work status early. "
        "Tell me your target role and I'll give more specific tips. (Connect an AI provider for richer answers.)"
    )
