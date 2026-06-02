"""Direct messaging: 1-on-1 conversations and messages."""
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_request = models.BooleanField(default=False)  # pending message request
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="initiated_conversations")

    class Meta:
        ordering = ["-updated_at"]

    @classmethod
    def between(cls, user_a, user_b):
        """Get or create the 1-on-1 conversation between two users."""
        convo = (cls.objects.filter(participants=user_a)
                            .filter(participants=user_b).first())
        if convo:
            return convo
        convo = cls.objects.create()
        convo.participants.add(user_a, user_b)
        return convo

    def __str__(self):
        return f"Conversation #{self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.full_name}: {self.body[:30]}"
