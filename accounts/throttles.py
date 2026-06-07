"""Scoped throttles for sensitive auth/abuse-prone endpoints.

Each class sets a `scope` whose rate is defined in settings.DEFAULT_THROTTLE_RATES.
Keying is by client IP (and email for login) so brute force is limited per source.
"""
from rest_framework.throttling import SimpleRateThrottle


class _IpScopedThrottle(SimpleRateThrottle):
    scope = "default"

    def get_cache_key(self, request, view):
        if not self.THROTTLE_RATES.get(self.scope):
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginThrottle(_IpScopedThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        email = ""
        try:
            email = (request.data.get("email") or "").strip().lower()
        except Exception:
            pass
        key = f"{email}:{ident}" if email else ident
        return self.cache_format % {"scope": self.scope, "ident": key}


class RegisterThrottle(_IpScopedThrottle):
    scope = "register"


class PasswordResetThrottle(_IpScopedThrottle):
    scope = "password_reset"


class ResendVerificationThrottle(_IpScopedThrottle):
    scope = "resend_verification"


class CVThrottle(_IpScopedThrottle):
    scope = "cv"


class SharePreviewThrottle(_IpScopedThrottle):
    scope = "share_preview"


class GoogleLoginThrottle(_IpScopedThrottle):
    scope = "google_login"
