from rest_framework import serializers
from .models import Conversation, Message
from posts.serializers import AuthorSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = AuthorSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender", "body", "is_ai", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "is_ai", "is_read", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_title = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "kind", "title", "display_title", "image_url", "participant_count",
                  "other_user", "last_message", "unread_count", "updated_at", "is_request", "initiator_id"]

    def _me(self):
        return self.context["request"].user

    def get_other_user(self, obj):
        if obj.kind != Conversation.Kind.DIRECT:
            return None
        other = obj.participants.exclude(pk=self._me().pk).first()
        return AuthorSerializer(other, context=self.context).data if other else None

    def get_display_title(self, obj):
        if obj.kind == Conversation.Kind.AI:
            return "AI Career Assistant"
        if obj.kind == Conversation.Kind.DIRECT:
            other = obj.participants.exclude(pk=self._me().pk).first()
            return other.full_name if other else "Conversation"
        return obj.title or "Group"

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return ""

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_last_message(self, obj):
        msg = obj.messages.last()
        return MessageSerializer(msg, context=self.context).data if msg else None

    def get_unread_count(self, obj):
        return obj.messages.filter(is_read=False).exclude(sender=self._me()).count()
