from django.db import migrations


SPONSORS = [
    ("Revolut", "Fintech", "https://www.revolut.com/careers/", "https://www.linkedin.com/company/revolut/jobs/", "confirmed"),
    ("Monzo Bank", "Fintech", "https://monzo.com/careers/", "https://www.linkedin.com/company/monzo-bank/jobs/", "confirmed"),
    ("Deloitte UK", "Consulting", "https://www.deloitte.com/uk/en/careers.html", "https://www.linkedin.com/company/deloitte/jobs/", "confirmed"),
    ("Arm", "Semiconductors", "https://www.arm.com/careers", "https://www.linkedin.com/company/arm/jobs/", "confirmed"),
    ("AstraZeneca", "Pharmaceuticals", "https://careers.astrazeneca.com/", "https://www.linkedin.com/company/astrazeneca/jobs/", "confirmed"),
    ("NHS", "Healthcare", "https://www.jobs.nhs.uk/", "https://www.linkedin.com/company/nhs/jobs/", "confirmed"),
]

# Sample roles that link to the real careers page (no scraping; pointer entries).
JOBS = [
    ("Graduate Software Engineer", "Revolut", "London", "graduate", "£45,000 - £60,000", "Python, React, SQL", "graduate"),
    ("Data Analyst", "Monzo Bank", "London", "full_time", "£40,000 - £55,000", "SQL, Python, Looker", "entry"),
    ("Consulting Analyst (Graduate Scheme)", "Deloitte UK", "London", "graduate", "£32,000 - £38,000", "Communication, Excel", "graduate"),
    ("Software Engineering Internship", "Arm", "Cambridge", "internship", "£28,000 pro rata", "C++, Python", "entry"),
    ("Clinical Data Associate", "AstraZeneca", "Cambridge", "full_time", "£35,000 - £45,000", "Data, Pharma", "mid"),
    ("Healthcare Assistant", "NHS", "Manchester", "full_time", "£22,000 - £25,000", "Care, Communication", "entry"),
]


def seed(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    SponsorCompany = apps.get_model("jobs", "SponsorCompany")
    careers = {}
    for name, industry, c_url, li_url, conf in SPONSORS:
        obj, _ = SponsorCompany.objects.get_or_create(
            name=name,
            defaults=dict(industry=industry, country="UK", careers_url=c_url,
                          linkedin_url=li_url, sponsorship_confidence=conf),
        )
        careers[name] = c_url
    for title, company, location, jtype, salary, skills, exp in JOBS:
        Job.objects.get_or_create(
            title=title, company=company,
            defaults=dict(location=location, country="UK", job_type=jtype,
                          visa_sponsorship=True, salary_range=salary, experience_level=exp,
                          skills=skills, apply_url=careers.get(company, "https://www.gov.uk/find-a-job"),
                          posted_by="Kommunitea", is_active=True,
                          description=f"{title} at {company}. Visa sponsorship available. Apply via the official careers page."),
        )


def unseed(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    SponsorCompany = apps.get_model("jobs", "SponsorCompany")
    Job.objects.filter(posted_by="Kommunitea").delete()
    SponsorCompany.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("jobs", "0002_sponsorcompany_job_country_job_experience_level_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
