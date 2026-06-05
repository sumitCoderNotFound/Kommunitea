"""Community member models for UK Job Tribe."""
from django.db import models


class Member(models.Model):
    """A job seeker who joins the UK Job Tribe community."""

    class UKStatus(models.TextChoices):
        STUDENT = "student", "Student"
        PSW = "psw", "Post Study Work Visa (PSW)"
        EMPLOYED = "employed", "Currently Employed"
        OTHER = "other", "Other"

    class Field(models.TextChoices):
        SOFTWARE = "software", "Software Development"
        DATA_AI = "data_ai", "Data / AI / ML"
        PROJECT_MGMT = "project_management", "Project Management"
        NON_TECH = "non_tech", "Non-tech"
        OTHER = "other", "Other"

    class Experience(models.TextChoices):
        JUNIOR = "0-1", "0–1 years"
        MID = "2-3", "2–3 years"
        SENIOR = "4-6", "4–6 years"
        EXPERT = "7+", "7+ years"

    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=80)
    uk_status = models.CharField(max_length=20, choices=UKStatus.choices)
    professional_field = models.CharField(max_length=30, choices=Field.choices)
    experience = models.CharField(max_length=10, choices=Experience.choices)
    looking_for = models.CharField(max_length=200, blank=True)
    biggest_challenge = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.city})"


class Community(models.Model):
    """A joinable community (university, tech, startups, housing, events, etc.)."""
    from django.conf import settings as _settings

    class Category(models.TextChoices):
        UNIVERSITY = "university", "Universities"
        TECHNOLOGY = "technology", "Technology"
        STARTUPS = "startups", "Startups"
        JOBS = "jobs", "Jobs"
        HOUSING = "housing", "Housing"
        EVENTS = "events", "Events"
        OTHER = "other", "Other"

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    image = models.ImageField(upload_to="communities/", blank=True, null=True)
    members = models.ManyToManyField("accounts.User", related_name="communities", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """A showcase project a user adds to their profile."""
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    image = models.ImageField(upload_to="projects/", blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
