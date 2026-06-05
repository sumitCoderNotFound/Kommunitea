from django.db import migrations


def seed(apps, schema_editor):
    Community = apps.get_model("community", "Community")
    starters = [
        ("UK Students Hub", "university", "Connect with students across UK universities."),
        ("Tech & Software", "technology", "Developers, engineers and tech enthusiasts."),
        ("Startups & Founders", "startups", "Build, pitch and grow your startup."),
        ("Graduate Jobs UK", "jobs", "Graduate schemes, internships and job leads."),
        ("Student Housing", "housing", "Find flatmates and housing near campus."),
        ("Events & Meetups", "events", "Networking events, hackathons and socials."),
        ("Data, AI & ML", "technology", "Everything data science, AI and machine learning."),
        ("Career Switchers", "jobs", "Support for changing careers in the UK."),
    ]
    for name, cat, desc in starters:
        Community.objects.get_or_create(name=name, defaults={"category": cat, "description": desc})


def unseed(apps, schema_editor):
    Community = apps.get_model("community", "Community")
    Community.objects.filter(name__in=[
        "UK Students Hub", "Tech & Software", "Startups & Founders", "Graduate Jobs UK",
        "Student Housing", "Events & Meetups", "Data, AI & ML", "Career Switchers",
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [("community", "0002_community_project")]
    operations = [migrations.RunPython(seed, unseed)]
