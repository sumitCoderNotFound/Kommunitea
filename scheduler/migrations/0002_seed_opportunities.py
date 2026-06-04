from datetime import date
from django.db import migrations


def seed(apps, schema_editor):
    Opportunity = apps.get_model("scheduler", "Opportunity")
    if Opportunity.objects.filter(user__isnull=True).exists():
        return
    rows = [
        # Upcoming opportunities
        dict(kind="opportunity", title="Amazon Graduate Scheme", org="Amazon", deadline=date(2026, 11, 25)),
        dict(kind="opportunity", title="JP Morgan Internship", org="JP Morgan", deadline=date(2026, 11, 27)),
        dict(kind="opportunity", title="Northumbria Career Fair", org="Northumbria University", location="Newcastle", deadline=date(2026, 11, 24)),
        # Community events
        dict(kind="event", title="AI Meetup Newcastle", location="Newcastle"),
        dict(kind="event", title="Northumbria Career Workshop", location="Online"),
        dict(kind="event", title="Hackathon Team Meeting", location="London"),
        dict(kind="event", title="Startup Networking Event", location="Manchester"),
    ]
    for r in rows:
        Opportunity.objects.create(user=None, **r)


def unseed(apps, schema_editor):
    Opportunity = apps.get_model("scheduler", "Opportunity")
    Opportunity.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("scheduler", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
