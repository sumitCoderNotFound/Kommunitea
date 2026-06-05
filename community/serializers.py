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
    image_url = serializers.SerializerMethodField()
    image = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Project
        fields = ["id", "title", "description", "url", "tags", "image", "image_url", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url
