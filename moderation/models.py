"""Reports and blocks for community safety."""
from django.conf import settings
from django.db import models


class Report(models.Model):
    class Target(models.TextChoices):
        POST = "post", "Post"
        COMMENT = "comment", "Comment"
        USER = "user", "User"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam or scam"
        HARASSMENT = "harassment", "Harassment or bullying"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        MISINFORMATION = "misinformation", "Misinformation"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    target_type = models.CharField(max_length=10, choices=Target.choices)
    target_id = models.IntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    detail = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_target_type_display()} #{self.target_id} - {self.reason}"


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocking")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocker", "blocked")

    def __str__(self):
        return f"{self.blocker_id} blocks {self.blocked_id}"
