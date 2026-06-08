"""Clips: short useful videos (UK life, jobs, study, visa, city guides, community).

Familiar vertical-video UX, but Kommunitea-specific via contextual links (job,
community, city, university, course). Video stored on S3 (same storage as posts).
Duration/size validated client-side now; `status` field is ready for real
server-side processing later. Only verified users may upload.
"""
from django.conf import settings
from django.db import models


class Clip(models.Model):
    class Category(models.TextChoices):
        UK_LIFE = "uk_life", "UK Life"
        JOBS = "jobs", "Jobs"
        ACCOMMODATION = "accommodation", "Accommodation"
        STUDY = "study", "Study"
        VISA = "visa", "Visa"
        CAREER = "career", "Career"
        PROJECTS = "projects", "Projects"
        CITY_GUIDES = "city_guides", "City Guides"
        COMMUNITY = "community", "Community"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS_ONLY = "followers_only", "Followers only"
        COMMUNITY_ONLY = "community_only", "Community only"
        PRIVATE = "private", "Private"

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clips")
    caption = models.TextField(blank=True)
    video_file = models.FileField(upload_to="clips/")
    thumbnail = models.ImageField(upload_to="clips/thumbs/", blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size = models.PositiveBigIntegerField(default=0)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.UK_LIFE, db_index=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    tags = models.JSONField(default=list, blank=True)  # hashtags / keywords

    # Optional contextual links (the Kommunitea-specific part).
    community = models.ForeignKey("community.Community", on_delete=models.SET_NULL, null=True, blank=True, related_name="clips")
    related_job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="clips")
    related_university = models.ForeignKey("study_match.University", on_delete=models.SET_NULL, null=True, blank=True, related_name="clips")
    related_course = models.ForeignKey("study_match.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="clips")
    related_city_slug = models.SlugField(max_length=140, blank=True)  # references CityStudyData.slug

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.READY)
    views_count = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_clips", blank=True)
    saved_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="saved_clips", blank=True)
    shares_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "-created_at"])]

    def __str__(self):
        return f"Clip {self.id} by {self.user_id}"

    @property
    def likes_count(self):
        return self.liked_by.count()

    @property
    def saves_count(self):
        return self.saved_by.count()

    @property
    def comments_count(self):
        return self.comments.count()

    def visible_to(self, user):
        """Privacy gate: status, blocks (either direction), then visibility."""
        if self.status in (self.Status.REJECTED, self.Status.FAILED):
            return user == self.user
        owner = self.user
        if user and user.is_authenticated:
            if user == owner:
                return True
            # Hide if either party blocks the other.
            from moderation.models import Block
            if Block.objects.filter(blocker=owner, blocked=user).exists():
                return False
            if Block.objects.filter(blocker=user, blocked=owner).exists():
                return False
        if self.visibility == self.Visibility.PUBLIC:
            return True
        if not (user and user.is_authenticated):
            return False
        if self.visibility == self.Visibility.FOLLOWERS_ONLY:
            return owner.followers.filter(pk=user.pk).exists()
        if self.visibility == self.Visibility.COMMUNITY_ONLY and self.community_id:
            return self.community.members.filter(pk=user.pk).exists()
        return False


class ClipComment(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class ClipReport(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("clip", "reporter")
