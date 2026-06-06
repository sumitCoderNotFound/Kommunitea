from rest_framework import serializers
from .models import Job, SponsorCompany


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id", "title", "company", "location", "country", "job_type",
            "visa_sponsorship", "salary_range", "experience_level", "skills",
            "description", "apply_url", "posted_by", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SponsorCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsorCompany
        fields = [
            "id", "name", "industry", "country",
            "careers_url", "linkedin_url", "sponsorship_confidence", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
