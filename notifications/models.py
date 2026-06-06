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
        FOLLOW_ACCEPTED = "follow_accepted", "accepted your follow request"
        STORY_LIKE = "story_like", "liked your story"
        STORY_REPLY = "story_reply", "replied to your story"
        STORY_SHARE = "story_share", "shared your story"
        STREAK = "streak", "reached a streak milestone"
        MESSAGE_REACTION = "message_reaction", "reacted to your message"
        VIEW_ONCE_OPENED = "view_once_opened", "opened your photo"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    verb = models.CharField(max_length=20, choices=Verb.choices)
    text = models.CharField(max_length=255, blank=True)
    post_id = models.IntegerField(null=True, blank=True)
    # navigation targets so a tap opens the exact item
    conversation_id = models.CharField(max_length=64, blank=True)
    target_type = models.CharField(max_length=24, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    story_id = models.CharField(max_length=64, blank=True)
    user_id = models.CharField(max_length=64, blank=True)
    job_id = models.CharField(max_length=64, blank=True)
    community_id = models.CharField(max_length=64, blank=True)
    reshare_id = models.CharField(max_length=64, blank=True)
    event_id = models.CharField(max_length=64, blank=True)
    referral_id = models.CharField(max_length=64, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def push(cls, recipient, actor, verb, text="", post_id=None, **targets):
        # Don't notify yourself (streak is the one self-notification we allow)
        if recipient == actor and verb != cls.Verb.STREAK:
            return None
        allowed = {"conversation_id", "target_type", "target_id", "story_id",
                   "user_id", "job_id", "event_id", "referral_id", "community_id", "reshare_id"}
        extra = {k: str(v) for k, v in targets.items() if k in allowed and v is not None}
        return cls.objects.create(recipient=recipient, actor=actor, verb=verb,
                                  text=text, post_id=post_id, **extra)

    def __str__(self):
        return f"{self.actor.full_name} {self.get_verb_display()}"
