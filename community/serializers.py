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
