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
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    visa_sponsorship = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    apply_url = models.URLField()
    posted_by = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company}"
