from django.db import migrations

INTL_JOBS = [
    ("Software Engineer", "Shopify", "Toronto", "Canada", "full_time", "CAD 90,000 - 120,000", "Ruby, React", "mid", "https://www.shopify.com/careers"),
    ("Data Scientist", "SAP", "Berlin", "Germany", "full_time", "EUR 60,000 - 80,000", "Python, ML", "mid", "https://jobs.sap.com/"),
    ("Frontend Developer", "Booking.com", "Amsterdam", "Netherlands", "full_time", "EUR 55,000 - 75,000", "React, TypeScript", "mid", "https://careers.booking.com/"),
    ("Graduate Software Engineer", "Atlassian", "Sydney", "Australia", "graduate", "AUD 85,000 - 100,000", "Java, React", "graduate", "https://www.atlassian.com/company/careers"),
    ("Machine Learning Engineer", "Nvidia", "Santa Clara", "USA", "full_time", "USD 130,000 - 180,000", "Python, CUDA", "senior", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
    ("Business Analyst", "Spotify", "New York", "USA", "full_time", "USD 90,000 - 120,000", "SQL, Analytics", "mid", "https://www.lifeatspotify.com/jobs"),
]

def seed(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    for title, company, location, country, jtype, salary, skills, exp, url in INTL_JOBS:
        Job.objects.get_or_create(
            title=title, company=company,
            defaults=dict(location=location, country=country, job_type=jtype,
                          visa_sponsorship=True, salary_range=salary, experience_level=exp,
                          skills=skills, apply_url=url, posted_by="Kommunitea", is_active=True,
                          description=f"{title} at {company} ({country}). Visa sponsorship available. Apply via the official careers page."),
        )

def unseed(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(company__in=[j[1] for j in INTL_JOBS]).delete()

class Migration(migrations.Migration):
    dependencies = [("jobs", "0003_seed_sponsors")]
    operations = [migrations.RunPython(seed, unseed)]
