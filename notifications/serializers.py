from rest_framework import serializers
from .models import Notification
from posts.serializers import AuthorSerializer


class NotificationSerializer(serializers.ModelSerializer):
    actor = AuthorSerializer(read_only=True)
    verb_display = serializers.CharField(source="get_verb_display", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "actor", "verb", "verb_display", "text", "post_id",
                  "conversation_id", "target_type", "target_id", "story_id",
                  "user_id", "job_id", "event_id", "referral_id", "community_id", "reshare_id",
                  "is_read", "created_at"]
