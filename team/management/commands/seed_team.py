"""Seed the database with the real UK Job Tribe team."""
from django.core.management.base import BaseCommand
from team.models import TeamMember

TEAM = [
    ("Mujammil Murtaza Shaik", "tech", "Leeds", "Frontend, PM", "7+ years", "mujammilmurtazas@gmail.com"),
    ("Balaji Sudharsan", "tech", "Milton Keynes", "Data/ML, PM", "7+ years", "gates002uk@gmail.com"),
    ("Faraz Mohammed", "tech", "London", "Frontend, Backend, UI/UX, PM", "2-3 years", "Mohdfaraz4yahoo@gmail.com"),
    ("Aakash Vishwakarma", "tech", "Coventry", "Data/ML, PM", "2-3 years", "aakashvishwakarma29@gmail.com"),
    ("Prathvi Patel", "tech", "London", "Backend, Data/ML", "2-3 years", "prathvip98@gmail.com"),
    ("Shubh Butani", "tech", "London", "UI/UX Design", "2-3 years", "shubhbutani15@gmail.com"),
    ("Sagar Marvadi", "social", "Stratford", "SEO, Social Media, Google Ads", "6+ years", "Sagar64.sm@gmail.com"),
]


class Command(BaseCommand):
    help = "Seed the real UJT team members"

    def handle(self, *args, **options):
        for order, (name, role, city, skills, exp, email) in enumerate(TEAM):
            obj, created = TeamMember.objects.update_or_create(
                email=email,
                defaults={"name": name, "role": role, "city": city,
                          "skills": skills, "experience": exp,
                          "display_order": order, "is_active": True},
            )
            self.stdout.write(("Created " if created else "Updated ") + name)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(TEAM)} team members"))
