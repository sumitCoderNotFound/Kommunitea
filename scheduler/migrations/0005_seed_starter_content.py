from django.db import migrations
from datetime import date, timedelta


COMMUNITIES = [
    ("Newcastle Students", "university", "Students living and studying in Newcastle."),
    ("Northumbria University", "university", "The Northumbria University community on Kommunitea."),
    ("Accommodation Help UK", "housing", "Find rooms, flatmates and housing across the UK."),
    ("Software Engineers UK", "technology", "Developers and engineers working or studying in the UK."),
    ("Visa Help UK", "other", "Student visas, PSW, Skilled Worker and immigration questions."),
    ("Part-Time Jobs UK", "jobs", "Part-time roles, shifts and student-friendly work."),
    ("Food & Lifestyle UK", "events", "Food, lifestyle, places to go and things to do."),
    ("Project Collaboration UK", "technology", "Find teammates and collaborators for your projects."),
]

POSTS = [
    ("jobs", "How to find part-time jobs in the UK: start with your university job shop, supermarkets, hospitality and campus roles. Keep a simple CV ready and apply early in the week."),
    ("university_life", "Building a UK CV: keep it to 1-2 pages, lead with a short personal statement, list skills clearly, and tailor it to each role. Avoid photos and date of birth."),
    ("accommodation", "Best areas to live near university: balance rent, commute and safety. Ask current students, view in person where possible, and never pay a deposit before seeing a contract."),
    ("visa_psw", "What to do after arriving in the UK: get a SIM, open a bank account, register with a GP, collect your BRP, and set up your student ID and travel card."),
    ("jobs", "How referrals work in the UK: a referral is someone inside a company recommending you. Build genuine connections, then politely ask if they would refer you for a specific role."),
    ("collaboration", "Looking for project teammates? Share what you're building, the roles you need, and your timeline. Great projects are the best portfolio pieces for UK job applications."),
]

OPPORTUNITIES = [
    ("event", "Northumbria Career Fair", "Northumbria University", "Newcastle", 21),
    ("opportunity", "Graduate Scheme Deadline", "Major UK Employers", "UK", 30),
    ("opportunity", "Summer Internship Deadline", "Tech Companies", "UK", 25),
    ("event", "Tech Networking Meetup", "Newcastle Tech", "Newcastle", 10),
    ("event", "CV & Interview Workshop", "Careers Service", "Online", 7),
]


def seed(apps, schema_editor):
    Community = apps.get_model("community", "Community")
    User = apps.get_model("accounts", "User")
    Post = apps.get_model("posts", "Post")
    Opportunity = apps.get_model("scheduler", "Opportunity")

    for name, cat, desc in COMMUNITIES:
        Community.objects.get_or_create(name=name, defaults={"category": cat, "description": desc})

    # A system author for starter posts (not a login account; unusable password).
    from django.contrib.auth.hashers import make_password
    system, created = User.objects.get_or_create(
        email="team@kommunitea.com",
        defaults={"full_name": "Kommunitea Team", "is_verified": True,
                  "user_type": "professional", "password": make_password(None)},
    )

    for cat, body in POSTS:
        Post.objects.get_or_create(author=system, body=body, defaults={"category": cat})

    today = date.today()
    for kind, title, org, loc, days in OPPORTUNITIES:
        Opportunity.objects.get_or_create(
            title=title, user=None,
            defaults={"kind": kind, "org": org, "location": loc, "deadline": today + timedelta(days=days)},
        )


def unseed(apps, schema_editor):
    Community = apps.get_model("community", "Community")
    Post = apps.get_model("posts", "Post")
    Opportunity = apps.get_model("scheduler", "Opportunity")
    User = apps.get_model("accounts", "User")
    Community.objects.filter(name__in=[c[0] for c in COMMUNITIES]).delete()
    Opportunity.objects.filter(title__in=[o[1] for o in OPPORTUNITIES], user=None).delete()
    Post.objects.filter(body__in=[p[1] for p in POSTS]).delete()
    User.objects.filter(email="team@kommunitea.com").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("scheduler", "0004_alter_weeklygoal_week_start"),
        ("community", "0004_project_category_project_cover_image_and_more"),
        ("posts", "0003_story_liked_by_story_visibility"),
        ("accounts", "0008_user_arrival_date_user_company_website_and_more"),
    ]
    operations = [migrations.RunPython(seed, unseed)]
