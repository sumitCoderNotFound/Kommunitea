"""Job board models for UK Job Tribe."""
from django.db import models


class Job(models.Model):
    """A job opportunity shared within the community."""

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        GRADUATE = "graduate", "Graduate Scheme"

    title = models.CharField(max_length=150)
    company = models.CharField(max_length=120)
    location = models.CharField(max_length=120)
    country = models.CharField(max_length=60, default="UK")
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    visa_sponsorship = models.BooleanField(default=False)
    salary_range = models.CharField(max_length=80, blank=True)
    experience_level = models.CharField(max_length=40, blank=True)  # entry / graduate / mid / senior
    skills = models.CharField(max_length=240, blank=True)  # comma-separated
    description = models.TextField(blank=True)
    apply_url = models.URLField()
    posted_by = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company}"


class SponsorCompany(models.Model):
    """A company known to sponsor visas (seeded from public UK sponsor register / admin-added)."""
    class Confidence(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        LIKELY = "likely", "Likely"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=160)
    industry = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=60, default="UK")
    careers_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    sponsorship_confidence = models.CharField(max_length=12, choices=Confidence.choices, default=Confidence.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
