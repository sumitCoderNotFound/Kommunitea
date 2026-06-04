"""Scheduler: the Career & Life Operating System for Kommunitea.

Designed as the central hub where users manage tasks, deadlines, goals,
opportunities and community events. Architected so Tasks can later be created
from Jobs, Community Events, Referrals and Projects via the `source` fields.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    class Category(models.TextChoices):
        INTERVIEW = "interview", "Interview"
        JOB_DEADLINE = "job_deadline", "Job Deadline"
        ACCOMMODATION = "accommodation", "Accommodation"
        VISA = "visa", "Visa"
        UNIVERSITY = "university", "University"
        PROJECTS = "projects", "Projects"
        NETWORKING = "networking", "Networking"
        CAREER_FAIR = "career_fair", "Career Fair"
        COMMUNITY_EVENT = "community_event", "Community Event"
        PERSONAL_GOAL = "personal_goal", "Personal Goal"
        CERTIFICATION = "certification", "Certification"
        REFERRAL_FOLLOWUP = "referral_followup", "Referral Follow-up"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        JOB = "job", "Job"
        EVENT = "event", "Community Event"
        REFERRAL = "referral", "Referral"
        PROJECT = "project", "Project"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    due_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    # Future integration hooks: a Task may originate from another Kommunitea object.
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.MANUAL)
    source_ref = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["completed", "due_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # stamp/clear completion time so the consistency heatmap is accurate
        if self.completed and self.completed_at is None:
            self.completed_at = timezone.now()
        if not self.completed:
            self.completed_at = None
        super().save(*args, **kwargs)


class WeeklyGoal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_goals")
    title = models.CharField(max_length=160)
    target = models.PositiveIntegerField(default=1)
    progress = models.PositiveIntegerField(default=0)
    week_start = models.DateField(default=timezone.now)  # Monday of the goal's week
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def done(self):
        return self.progress >= self.target

    def __str__(self):
        return self.title


class Opportunity(models.Model):
    """Upcoming Opportunities + Community Events.

    Global rows (user is null) are visible to everyone; eventually these will be
    fed from the Jobs board and Community Events. Users can 'add to scheduler',
    which creates a Task (handled in the view).
    """
    class Kind(models.TextChoices):
        OPPORTUNITY = "opportunity", "Opportunity"
        EVENT = "event", "Community Event"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="opportunities", null=True, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.OPPORTUNITY)
    title = models.CharField(max_length=200)
    org = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["deadline", "created_at"]

    def __str__(self):
        return self.title
