"""Permission requiring a verified email for sensitive actions.

Gating is OFF unless settings.REQUIRE_EMAIL_VERIFICATION is True, so enabling
email delivery is what switches enforcement on — it won't lock out existing
users the moment this ships.
"""
from django.conf import settings
from rest_framework import permissions


class IsEmailVerified(permissions.BasePermission):
    message = "Please verify your email address to do this."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not getattr(settings, "REQUIRE_EMAIL_VERIFICATION", False):
            return True
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_email_verified", False))
