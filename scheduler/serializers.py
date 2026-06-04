from rest_framework import serializers
from .models import Task, WeeklyGoal, Opportunity


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "notes", "category", "priority", "due_at",
                  "completed", "completed_at", "source", "source_ref",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]


class WeeklyGoalSerializer(serializers.ModelSerializer):
    done = serializers.BooleanField(read_only=True)

    class Meta:
        model = WeeklyGoal
        fields = ["id", "title", "target", "progress", "done", "week_start", "created_at"]
        read_only_fields = ["id", "done", "created_at"]


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ["id", "kind", "title", "org", "location", "deadline", "created_at"]
        read_only_fields = ["id", "created_at"]
