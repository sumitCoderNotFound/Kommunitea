from rest_framework import serializers
from .models import Post, Comment


class AuthorSerializer(serializers.Serializer):
    """Lightweight author block embedded in posts/comments."""
    id = serializers.CharField()
    full_name = serializers.CharField()
    university = serializers.CharField(default="")
    badge = serializers.CharField(default="")
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if not getattr(obj, "avatar", None):
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def get_is_online(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        seen = getattr(obj, "last_seen", None)
        return bool(seen and seen > timezone.now() - timedelta(minutes=2))


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    saves_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    reshares_count = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    image = serializers.ImageField(write_only=True, required=False)

    def get_reshares_count(self, obj):
        return obj.reshares.count()

    class Meta:
        model = Post
        fields = [
            "id", "author", "body", "image", "image_url", "category",
            "visibility", "allow_reshare", "allow_share_to_story",
            "likes_count", "comments_count", "saves_count", "reshares_count",
            "is_liked", "is_saved", "comments", "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def get_likes_count(self, obj):
        return obj.liked_by.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_saves_count(self, obj):
        return obj.saved_by.count()

    def _user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_is_liked(self, obj):
        u = self._user()
        return bool(u and obj.liked_by.filter(pk=u.pk).exists())

    def get_is_saved(self, obj):
        u = self._user()
        return bool(u and obj.saved_by.filter(pk=u.pk).exists())


class StorySerializer(serializers.ModelSerializer):
    from .models import Story  # noqa
    author = AuthorSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    image = serializers.ImageField(write_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()

    class Meta:
        from .models import Story
        model = Story
        fields = ["id", "author", "image", "image_url", "caption", "visibility",
                  "likes_count", "is_liked", "views_count", "created_at", "expires_at"]
        read_only_fields = ["id", "author", "created_at", "expires_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def get_likes_count(self, obj):
        return obj.liked_by.count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return obj.liked_by.filter(pk=user.pk).exists()
        return False

    def get_views_count(self, obj):
        return obj.viewed_by.count()
