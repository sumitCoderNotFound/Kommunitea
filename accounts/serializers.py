"""Serializers for auth and profiles. Field names are camelCased by
djangorestframework-camel-case at the API boundary to match the React frontend."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
        )


class UserSerializer(serializers.ModelSerializer):
    """Full profile representation used by /auth/me and /profiles."""
    avatar_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()
    has_requested = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()

    def get_posts_count(self, obj):
        return obj.posts.count()

    class Meta:
        model = User
        fields = [
            "id", "full_name", "email", "avatar_url", "cover_image_url", "user_type",
            "university", "course", "study_level", "graduation_date", "intake_year",
            "student_email", "company", "job_title", "years_experience", "industry",
            "hiring_for", "display_company", "open_to_networking", "open_to_referrals",
            "open_to_mentoring", "target_role", "experience_level", "job_type", "cv_uploaded",
            "company_website", "content_niche", "instagram", "youtube", "tiktok", "creator_topics",
            "destination_city", "arrival_date", "newcomer_needs",
            "city", "status", "skills",
            "interests", "looking_for", "career_goals", "bio", "linkedin",
            "github", "portfolio", "is_verified", "badge", "is_onboarded",
            "followers_count", "following_count", "is_private",
            "allow_messages_from", "allow_story_sharing", "allow_post_reshare", "posts_count",
            "is_following", "has_requested",
            "streak_count", "longest_streak",
        ]
        read_only_fields = ["id", "email", "is_verified", "badge",
                            "followers_count", "following_count",
                            "streak_count", "longest_streak"]

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return request.user.following.filter(pk=obj.pk).exists()

    def get_has_requested(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.received_requests.filter(from_user=request.user).exists()

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return ""
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return ""
        request = self.context.get("request")
        url = obj.cover_image.url
        return request.build_absolute_uri(url) if request else url


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD  # email
