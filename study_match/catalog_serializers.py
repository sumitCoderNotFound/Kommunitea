from rest_framework import serializers

from .models import University, Course, SyncLog


class CourseSerializer(serializers.ModelSerializer):
    indicative_fee_band = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"

    def get_indicative_fee_band(self, obj):
        from .fee_bands import band_for_course
        return band_for_course(obj)


class UniversitySerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source="courses.count", read_only=True)

    class Meta:
        model = University
        fields = "__all__"


class UniversityDetailSerializer(UniversitySerializer):
    courses = CourseSerializer(many=True, read_only=True)


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = "__all__"
