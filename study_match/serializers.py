from rest_framework import serializers

from .models import StudyProfile, StudyMatchResult, SavedStudyOption, StudyTask


class StudyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyProfile
        exclude = ["user"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudyMatchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyMatchResult
        fields = [
            "id", "overall_summary", "country_scores", "course_recommendations",
            "university_recommendations", "city_recommendations", "career_market_insights",
            "visa_cost_checklist", "action_plan", "created_at",
        ]


class SavedStudyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedStudyOption
        exclude = ["user"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyTask
        exclude = ["user"]
        read_only_fields = ["id", "created_at", "linked_plan_task_id"]
