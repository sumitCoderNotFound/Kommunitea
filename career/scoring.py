"""Rule-based CV / ATS readiness scoring (no AI model)."""
import re

ACTION_VERBS = {
    "led", "built", "designed", "developed", "managed", "created", "improved", "launched",
    "delivered", "implemented", "achieved", "increased", "reduced", "optimised", "optimized",
    "analysed", "analyzed", "coordinated", "automated", "owned", "drove", "shipped",
}
DEFAULT_ROLES = ["Software Engineer", "Data Analyst", "Business Analyst", "Graduate Role"]
STOPWORDS = {"the", "and", "for", "with", "you", "our", "your", "are", "will", "this", "that",
             "have", "has", "from", "job", "role", "work", "team", "able", "must", "should",
             "a", "an", "to", "of", "in", "on", "is", "as", "be", "or", "we", "at", "by"}


def extract_text(file_obj, filename: str) -> str:
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(file_obj)
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        if name.endswith(".docx"):
            import docx
            d = docx.Document(file_obj)
            return "\n".join(p.text for p in d.paragraphs)
        # plain text fallback
        data = file_obj.read()
        return data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)
    except Exception:
        return ""


def _keywords(text: str):
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


def analyze(text: str, job_description: str = "") -> dict:
    t = text or ""
    low = t.lower()
    words = re.findall(r"\S+", t)
    word_count = len(words)
    passed, failed, improvements = [], [], []

    def check(cond, label, fix=None):
        (passed if cond else failed).append(label)
        if not cond and fix:
            improvements.append(fix)

    # Structural checks
    check(200 <= word_count <= 1200, "Healthy length (200-1200 words)",
          "Aim for 200-1200 words; current is %d." % word_count)
    check(bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", t)), "Contact email present",
          "Add a professional email address.")
    check(bool(re.search(r"\b(0\d{9,10}|\+?\d[\d ]{8,})\b", t)), "Phone number present",
          "Add a contact phone number.")
    check("linkedin" in low or "github" in low, "LinkedIn / GitHub link",
          "Add your LinkedIn (and GitHub if technical).")
    check(any(k in low for k in ("summary", "profile", "objective", "about")), "Summary / profile section",
          "Add a 2-3 line professional summary at the top.")
    check("skills" in low, "Skills section",
          "Add a dedicated Skills section with relevant tools.")
    check(any(k in low for k in ("experience", "employment", "work history")), "Work experience section",
          "Add a Work Experience section with roles and dates.")
    check(any(k in low for k in ("education", "university", "degree", "bsc", "msc", "ba ", "ma ")), "Education section",
          "Add an Education section.")
    bullets = len(re.findall(r"(^|\n)\s*[•\-\*\u2022]", t))
    check(bullets >= 4, "Uses bullet points", "Use bullet points to list achievements.")
    verbs_found = {v for v in ACTION_VERBS if re.search(r"\b" + re.escape(v) + r"\b", low)}
    check(len(verbs_found) >= 3, "Strong action verbs",
          "Start bullets with action verbs (led, built, improved...).")
    has_numbers = bool(re.search(r"\b\d+%|\b\d{2,}\b", t))
    check(has_numbers, "Measurable achievements",
          "Quantify impact with numbers and percentages.")
    check(word_count == 0 or len(t) / max(word_count, 1) < 12, "No obvious formatting noise",
          "Avoid heavy tables/columns; ATS parsers prefer simple layouts.")

    # Section scores (0-100 per area)
    section_scores = {
        "contact": 100 if ("@" in t) else 40,
        "summary": 100 if any(k in low for k in ("summary", "profile", "objective")) else 30,
        "skills": 100 if "skills" in low else 30,
        "experience": 100 if any(k in low for k in ("experience", "employment")) else 30,
        "education": 100 if any(k in low for k in ("education", "university", "degree")) else 40,
        "impact": 100 if has_numbers else 35,
    }

    total = len(passed) + len(failed)
    ats_score = round((len(passed) / total) * 100) if total else 0

    # Job match
    job_match_score = None
    missing_keywords = []
    if job_description.strip():
        jd_kw = [w for w in dict.fromkeys(_keywords(job_description)) if len(w) > 3]
        cv_kw = set(_keywords(t))
        present = [w for w in jd_kw if w in cv_kw]
        missing_keywords = [w for w in jd_kw if w not in cv_kw][:12]
        job_match_score = round((len(present) / len(jd_kw)) * 100) if jd_kw else None

    top_fixes = improvements[:3]

    # Recommended roles from skills hints
    roles = []
    if any(k in low for k in ("python", "django", "backend", "api")): roles.append("Backend Developer")
    if any(k in low for k in ("react", "frontend", "javascript", "css")): roles.append("Frontend Developer")
    if any(k in low for k in ("data", "sql", "analytics", "tableau")): roles.append("Data Analyst")
    if any(k in low for k in ("machine learning", "ml", "tensorflow", "pytorch")): roles.append("AI/ML Engineer")
    if not roles:
        roles = DEFAULT_ROLES[:3]

    summary = (
        f"Your CV passed {len(passed)} of {total} ATS readiness checks "
        f"({ats_score}/100). "
        + ("Strong job-description alignment. " if (job_match_score or 0) >= 70 else
           "Add more keywords from the job description. " if job_match_score is not None else "")
        + ("Focus on the top fixes below to improve parsing and impact."
           if top_fixes else "Your CV is in good shape for ATS systems.")
    )

    return {
        "ats_score": ats_score,
        "job_match_score": job_match_score,
        "section_scores": section_scores,
        "missing_keywords": missing_keywords,
        "passed_checks": passed,
        "failed_checks": failed,
        "improvement_checks": improvements,
        "top_fixes": top_fixes,
        "recommended_roles": roles[:4],
        "summary": summary,
    }
