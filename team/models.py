"""Team showcase models for UK Job Tribe."""
from django.db import models


class TeamMember(models.Model):
    """A core team member building UK Job Tribe projects."""

    class Role(models.TextChoices):
        TECH = "tech", "Tech Team"
        SOCIAL = "social", "Social Media / Marketing"
        LEAD = "lead", "Team Lead"

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TECH)
    city = models.CharField(max_length=80)
    skills = models.CharField(max_length=200)
    experience = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    avatar_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} — {self.get_role_display()}"
