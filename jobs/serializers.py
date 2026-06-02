from rest_framework import serializers
from .models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id", "title", "company", "location", "job_type",
            "visa_sponsorship", "description", "apply_url",
            "posted_by", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
