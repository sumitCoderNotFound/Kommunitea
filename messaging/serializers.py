from rest_framework import serializers
from .models import Conversation, Message
from posts.serializers import AuthorSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = AuthorSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender", "body", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "is_read", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "other_user", "last_message", "unread_count", "updated_at", "is_request", "initiator_id"]

    def _me(self):
        return self.context["request"].user

    def get_other_user(self, obj):
        other = obj.participants.exclude(pk=self._me().pk).first()
        return AuthorSerializer(other, context=self.context).data if other else None

    def get_last_message(self, obj):
        msg = obj.messages.last()
        return MessageSerializer(msg, context=self.context).data if msg else None

    def get_unread_count(self, obj):
        return obj.messages.filter(is_read=False).exclude(sender=self._me()).count()
