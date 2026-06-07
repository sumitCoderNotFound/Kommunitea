"""Serializers for auth and profiles. Field names are camelCased by
djangorestframework-camel-case at the API boundary to match the React frontend."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


from django.contrib.auth.password_validation import validate_password as dj_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .username_utils import normalize_username, username_error, is_available


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    username = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["id", "full_name", "username", "email", "password"]

    def validate_username(self, value):
        v = normalize_username(value)
        err = username_error(v)
        if err:
            raise serializers.ValidationError(err)
        if not is_available(v):
            raise serializers.ValidationError("That username is already taken.")
        return v

    def validate_password(self, value):
        # Build a throwaway user so similarity-to-email/name checks work.
        candidate = User(email=self.initial_data.get("email", ""), full_name=self.initial_data.get("full_name", ""))
        try:
            dj_validate_password(value, user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            username=validated_data["username"],
        )


class UserSerializer(serializers.ModelSerializer):
    """Full profile representation used by /auth/me and /profiles."""
    avatar_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()
    mutual_followers = serializers.SerializerMethodField()

    def get_mutual_followers(self, obj):
        """People the viewer follows who also follow this profile (up to 3 names + total)."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or request.user.pk == obj.pk:
            return {"names": [], "count": 0}
        mine = set(request.user.following.values_list("id", flat=True))
        theirs = obj.followers.filter(pk__in=mine)[:10]
        names = [u.full_name.split(" ")[0] for u in theirs]
        total = obj.followers.filter(pk__in=mine).count()
        return {"names": names[:3], "count": total}
    has_requested = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    profile_completion = serializers.IntegerField(read_only=True)

    def get_posts_count(self, obj):
        return obj.posts.count()

    class Meta:
        model = User
        fields = [
            "id", "full_name", "display_name", "username", "email", "is_email_verified",
            "auth_provider", "avatar_url", "cover_image_url", "user_type",
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
            "is_following", "has_requested", "mutual_followers",
            "streak_count", "longest_streak",
            "phone_country_code", "phone_number", "is_phone_verified",
            "whatsapp_opt_in", "profile_completion",
        ]
        read_only_fields = ["id", "email", "is_verified", "badge", "is_email_verified",
                            "auth_provider", "is_phone_verified", "profile_completion",
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

    def validate(self, attrs):
        # Accept an email OR a username in the "email" field.
        identifier = (attrs.get(self.username_field) or "").strip()
        if identifier and "@" not in identifier:
            match = User.objects.filter(username=identifier.lower()).first()
            if match:
                attrs[self.username_field] = match.email
        return super().validate(attrs)
