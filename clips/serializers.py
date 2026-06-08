from rest_framework import serializers

from posts.serializers import AuthorSerializer
from .models import Clip, ClipComment


class ClipCommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = ClipComment
        fields = ["id", "author", "body", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class ClipSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    video_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    saves_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    is_following_creator = serializers.SerializerMethodField()
    context_action = serializers.SerializerMethodField()

    class Meta:
        model = Clip
        fields = [
            "id", "user", "caption", "video_url", "thumbnail_url", "duration_seconds",
            "file_size", "category", "visibility", "tags", "status",
            "community", "related_job", "related_university", "related_course", "related_city_slug",
            "views_count", "likes_count", "saves_count", "comments_count", "shares_count",
            "is_liked", "is_saved", "is_following_creator", "context_action", "created_at",
        ]
        read_only_fields = ["id", "user", "status", "views_count", "shares_count", "created_at"]

    def _abs(self, f):
        if not f:
            return None
        try:
            url = f.url
        except ValueError:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and not url.startswith("http") else url

    def get_video_url(self, obj):
        return self._abs(obj.video_file)

    def get_thumbnail_url(self, obj):
        return self._abs(obj.thumbnail)

    def _me(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_is_liked(self, obj):
        me = self._me()
        return bool(me and obj.liked_by.filter(pk=me.pk).exists())

    def get_is_saved(self, obj):
        me = self._me()
        return bool(me and obj.saved_by.filter(pk=me.pk).exists())

    def get_is_following_creator(self, obj):
        me = self._me()
        return bool(me and me != obj.user and obj.user.followers.filter(pk=me.pk).exists())

    def get_context_action(self, obj):
        """The Kommunitea-specific contextual action — only when real data exists."""
        if obj.category == Clip.Category.ACCOMMODATION:
            return {"type": "accommodation", "label": "Save to Plan", "citySlug": obj.related_city_slug or None}
        if obj.category == Clip.Category.JOBS and obj.related_job_id:
            return {"type": "job", "label": "Save job", "jobId": obj.related_job_id}
        if obj.category == Clip.Category.STUDY:
            if obj.related_university_id:
                return {"type": "university", "label": "Save university", "universityId": obj.related_university_id}
            if obj.related_course_id:
                return {"type": "course", "label": "Save course", "courseId": obj.related_course_id}
            return {"type": "study", "label": "Open Study Match"}
        if obj.category == Clip.Category.VISA:
            return {"type": "visa", "label": "Open checklist"}
        if obj.category == Clip.Category.CITY_GUIDES and obj.related_city_slug:
            return {"type": "city", "label": "Open city guide", "citySlug": obj.related_city_slug}
        if obj.category == Clip.Category.COMMUNITY and obj.community_id:
            return {"type": "community", "label": "Join community", "communityId": obj.community_id}
        return None


class ClipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clip
        fields = [
            "caption", "video_file", "thumbnail", "duration_seconds", "file_size",
            "category", "visibility", "tags", "community", "related_job",
            "related_university", "related_course", "related_city_slug",
        ]

    def validate_duration_seconds(self, v):
        if v and v > 60:
            raise serializers.ValidationError("Clips must be 60 seconds or shorter.")
        return v

    def validate_file_size(self, v):
        if v and v > 100 * 1024 * 1024:
            raise serializers.ValidationError("Video must be 100MB or smaller.")
        return v
