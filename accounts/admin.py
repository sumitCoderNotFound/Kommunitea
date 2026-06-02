from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["full_name", "email", "university", "city", "status", "is_onboarded", "is_verified"]
    list_filter = ["status", "is_onboarded", "is_verified", "badge"]
    search_fields = ["full_name", "email", "university"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "avatar", "university", "course",
                                "graduation_date", "intake_year", "city", "status",
                                "skills", "interests", "looking_for", "career_goals",
                                "bio", "linkedin", "github", "portfolio")}),
        ("Status", {"fields": ("is_verified", "badge", "is_onboarded", "is_private", "following")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),
    )
    filter_horizontal = ("following", "groups", "user_permissions")

from .models import FollowRequest


@admin.register(FollowRequest)
class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ["from_user", "to_user", "created_at"]
