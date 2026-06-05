from rest_framework import serializers
from .models import Conversation, Message
from posts.serializers import AuthorSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = AuthorSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    viewed = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "sender", "body", "kind", "image_url", "file_url", "file_name", "gif_url",
                  "lat", "lng", "viewed", "reactions", "is_ai", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "kind", "image_url", "file_url", "gif_url", "viewed",
                            "reactions", "is_ai", "is_read", "created_at"]

    def _me(self):
        req = self.context.get("request")
        return req.user if req else None

    def get_image_url(self, obj):
        if obj.kind == Message.Kind.VIEW_ONCE and obj.viewed_at is not None:
            return ""
        if obj.image:
            req = self.context.get("request")
            return req.build_absolute_uri(obj.image.url) if req else obj.image.url
        return ""

    def get_file_url(self, obj):
        if obj.file:
            req = self.context.get("request")
            return req.build_absolute_uri(obj.file.url) if req else obj.file.url
        return ""

    def get_viewed(self, obj):
        return obj.kind == Message.Kind.VIEW_ONCE and obj.viewed_at is not None

    def get_reactions(self, obj):
        me = self._me()
        out = {}
        for r in obj.reactions.all():
            entry = out.setdefault(r.emoji, {"emoji": r.emoji, "count": 0, "mine": False})
            entry["count"] += 1
            if me and r.user_id == me.pk:
                entry["mine"] = True
        return list(out.values())


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
