from django.conf import settings
from django.db import models


class ExternalShare(models.Model):
    """A piece of content a user brought into Kommunitea from elsewhere.

    Never scraped automatically — only created when the user pastes a link/text
    or shares into the app. Keeps the original source + attribution.
    """

    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        WHATSAPP = "whatsapp", "WhatsApp"
        WEBSITE = "website", "Website"
        TEXT = "text", "Text"

    class Destination(models.TextChoices):
        POST = "post", "Post"
        STORY = "story", "Story"
        COMMUNITY_RESOURCE = "community_resource", "Community resource"
        MESSAGE = "message", "Message"
        PLAN = "plan", "Plan task"
        JOB_APPLICATION = "job_application", "Job application"
        SAVED = "saved", "Saved only"

    class Status(models.TextChoices):
        PREVIEWED = "previewed", "Previewed"
        IMPORTED = "imported", "Imported"
        REMOVED = "removed", "Removed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="external_shares")
    source_platform = models.CharField(max_length=16, choices=Platform.choices, default=Platform.WEBSITE)
    source_url = models.URLField(blank=True, max_length=1000)
    source_text = models.TextField(blank=True)
    source_image = models.URLField(blank=True, max_length=1000)
    source_video = models.URLField(blank=True, max_length=1000)
    title = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.URLField(blank=True, max_length=1000)
    destination_type = models.CharField(max_length=20, choices=Destination.choices, blank=True)
    destination_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IMPORTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_source_platform_display()} → {self.destination_type} ({self.user_id})"
