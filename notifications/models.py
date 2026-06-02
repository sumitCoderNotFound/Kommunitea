"""Activity notifications (likes, comments, follows, messages)."""
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Verb(models.TextChoices):
        LIKE = "like", "liked your post"
        COMMENT = "comment", "commented on your post"
        FOLLOW = "follow", "started following you"
        REQUEST = "request", "requested to follow you"
        MESSAGE = "message", "sent you a message"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    verb = models.CharField(max_length=20, choices=Verb.choices)
    text = models.CharField(max_length=255, blank=True)
    post_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def push(cls, recipient, actor, verb, text="", post_id=None):
        # Don't notify yourself
        if recipient == actor:
            return None
        return cls.objects.create(recipient=recipient, actor=actor, verb=verb, text=text, post_id=post_id)

    def __str__(self):
        return f"{self.actor.full_name} {self.get_verb_display()}"
