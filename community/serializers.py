from rest_framework import serializers
from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "id", "full_name", "email", "city", "uk_status",
            "professional_field", "experience", "looking_for",
            "biggest_challenge", "linkedin", "is_approved", "created_at",
        ]
        read_only_fields = ["id", "is_approved", "created_at"]

    def validate_email(self, value):
        return value.lower().strip()


from .models import Community, Project


class CommunitySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ["id", "name", "description", "category", "image_url",
                  "members_count", "is_member", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def get_members_count(self, obj):
        return obj.members.count()

    def get_is_member(self, obj):
        request = self.context.get("request")
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and obj.members.filter(pk=u.pk).exists())


class ProjectSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(write_only=True, required=False)
    cover_image_url = serializers.SerializerMethodField()
    screenshot_urls = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "title", "tagline", "description", "category", "status",
            "cover_image", "cover_image_url", "screenshot_urls", "demo_video",
            "tech_stack", "links", "looking_for_collaborators", "roles_needed",
            "visibility", "owner", "is_owner", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "cover_image_url", "screenshot_urls", "owner", "is_owner", "created_at", "updated_at"]

    def _abs(self, image):
        if not image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(image.url) if request else image.url

    def get_cover_image_url(self, obj):
        return self._abs(obj.cover_image or obj.image)  # fall back to legacy image

    def get_screenshot_urls(self, obj):
        return [self._abs(s.image) for s in obj.screenshots.all()]

    def get_owner(self, obj):
        return {
            "id": str(obj.owner_id),
            "fullName": obj.owner.full_name,
            "avatarUrl": self._abs(getattr(obj.owner, "avatar", None)),
        }

    def get_is_owner(self, obj):
        req = self.context.get("request")
        return bool(req and obj.owner_id == req.user.pk)


from .models import CommunityEvent, CommunityResource


class CommunityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityEvent
        fields = ["id", "community", "title", "description", "location", "starts_at", "link", "created_at"]
        read_only_fields = ["id", "community", "created_at"]


class CommunityResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityResource
        fields = ["id", "community", "title", "kind", "url", "description", "created_at"]
        read_only_fields = ["id", "community", "created_at"]
