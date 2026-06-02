from rest_framework import serializers
from .models import TeamMember


class TeamMemberSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "name", "role", "role_display", "city", "skills",
            "experience", "email", "linkedin", "avatar_url",
            "display_order", "is_active",
        ]
        read_only_fields = ["id", "role_display"]
