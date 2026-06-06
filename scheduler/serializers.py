from rest_framework import serializers
from .models import Task, WeeklyGoal, Opportunity, JobApplication


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "notes", "category", "priority", "due_at",
                  "completed", "completed_at", "source", "source_ref",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]


class WeeklyGoalSerializer(serializers.ModelSerializer):
    done = serializers.BooleanField(read_only=True)
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyGoal
        fields = ["id", "title", "target", "progress", "kind", "status", "done",
                  "week_start", "applications_count", "created_at"]
        read_only_fields = ["id", "done", "applications_count", "created_at"]

    def get_applications_count(self, obj):
        return obj.applications.count()


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ["id", "goal", "job", "company", "role_title", "job_link", "source",
                  "status", "applied_date", "follow_up_date", "reminder_at", "notes",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ["id", "kind", "title", "org", "location", "deadline", "created_at"]
        read_only_fields = ["id", "created_at"]
