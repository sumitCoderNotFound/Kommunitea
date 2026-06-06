from rest_framework import serializers
from .models import CVAnalysis, ReferralRequest, InterviewPrep


class CVAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVAnalysis
        fields = ["id", "file_name", "ats_score", "job_match_score", "section_scores",
                  "missing_keywords", "passed_checks", "failed_checks", "improvement_checks",
                  "top_fixes", "recommended_roles", "summary", "created_at"]
        read_only_fields = fields


class ReferralRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralRequest
        fields = ["id", "job_application", "company", "role_title", "contact_user",
                  "contact_name", "contact_linkedin", "message", "status",
                  "follow_up_date", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewPrepSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrep
        fields = ["id", "job_application", "company", "role_title", "interview_date",
                  "checklist", "questions", "notes", "confidence_score",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
