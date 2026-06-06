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
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_communities")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """A showcase project a user adds to their profile (also used for collaboration)."""

    class Category(models.TextChoices):
        WEB_APP = "web_app", "Web App"
        MOBILE_APP = "mobile_app", "Mobile App"
        AI_ML = "ai_ml", "AI/ML"
        BACKEND = "backend", "Backend"
        FRONTEND = "frontend", "Frontend"
        FULL_STACK = "full_stack", "Full Stack"
        UI_UX = "ui_ux", "UI/UX"
        STARTUP_IDEA = "startup_idea", "Startup Idea"
        UNIVERSITY_PROJECT = "university_project", "University Project"
        OPEN_SOURCE = "open_source", "Open Source"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        LOOKING_FOR_TEAM = "looking_for_team", "Looking for Team"
        OPEN_TO_COLLAB = "open_to_collab", "Open to Collaboration"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers only"
        COMMUNITY = "community", "Community only"
        PRIVATE = "private", "Private"

    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=140)
    tagline = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.IDEA)
    cover_image = models.ImageField(upload_to="projects/", blank=True, null=True)
    demo_video = models.URLField(blank=True)
    tech_stack = models.JSONField(default=list, blank=True)        # ["React", "Django", ...]
    links = models.JSONField(default=list, blank=True)            # [{"type","label","url"}, ...]
    looking_for_collaborators = models.BooleanField(default=False)
    roles_needed = models.JSONField(default=list, blank=True)      # ["frontend", "backend", ...]
    visibility = models.CharField(max_length=12, choices=Visibility.choices, default=Visibility.PUBLIC)
    # legacy fields kept for backward compatibility with existing rows
    url = models.URLField(blank=True)
    image = models.ImageField(upload_to="projects/", blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ProjectScreenshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="screenshots")
    image = models.ImageField(upload_to="project_shots/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class CommunityEvent(models.Model):
    """A meetup / workshop / networking event linked to a community."""
    community = models.ForeignKey("community.Community", on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    link = models.URLField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "-created_at"]


class CommunityResource(models.Model):
    """A useful link / referral / visa / accommodation resource shared in a community."""
    class Kind(models.TextChoices):
        LINK = "link", "Useful link"
        JOB = "job", "Job / referral"
        VISA = "visa", "Visa"
        ACCOMMODATION = "accommodation", "Accommodation"

    community = models.ForeignKey("community.Community", on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.LINK)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_resources")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
