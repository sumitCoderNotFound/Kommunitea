"""Account management: username, change password, phone, WhatsApp preferences."""
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as dj_validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SecurityEvent
from .security import log_security_event
from .serializers import UserSerializer
from .throttles import _IpScopedThrottle
from .username_utils import normalize_username, username_error, is_available
from .otp_providers import get_otp_provider

User = get_user_model()


class UsernameCheckThrottle(_IpScopedThrottle):
    scope = "username_check"


class UsernameCheckView(APIView):
    """GET /api/auth/username/check/?username= → availability + validity."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UsernameCheckThrottle]

    def get(self, request):
        raw = request.query_params.get("username", "")
        v = normalize_username(raw)
        err = username_error(v)
        if err:
            return Response({"username": v, "available": False, "error": err})
        exclude = request.user.pk if request.user.is_authenticated else None
        available = is_available(v, exclude_user_id=exclude)
        return Response({
            "username": v, "available": available,
            "error": None if available else "That username is already taken.",
        })


class UsernameUpdateView(APIView):
    """PATCH /api/auth/username/ → set/change the current user's handle."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        v = normalize_username(request.data.get("username", ""))
        err = username_error(v)
        if err:
            return Response({"username": [err]}, status=status.HTTP_400_BAD_REQUEST)
        if not is_available(v, exclude_user_id=request.user.pk):
            return Response({"username": ["That username is already taken."]}, status=status.HTTP_400_BAD_REQUEST)
        request.user.username = v
        request.user.save(update_fields=["username"])
        log_security_event(SecurityEvent.Type.USERNAME_CHANGED, request=request, user=request.user, username=v)
        return Response(UserSerializer(request.user, context={"request": request}).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ — requires the current password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current = request.data.get("currentPassword") or request.data.get("current_password") or ""
        new = request.data.get("newPassword") or request.data.get("new_password") or ""
        user = request.user
        if user.has_usable_password() and not user.check_password(current):
            return Response({"detail": "Your current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            dj_validate_password(new, user=user)
        except DjangoValidationError as e:
            return Response({"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new)
        user.save(update_fields=["password"])
        log_security_event(SecurityEvent.Type.PASSWORD_CHANGED, request=request, user=user)
        return Response({"detail": "Password updated."})


class PhoneUpdateView(APIView):
    """PATCH /api/profile/phone/ — save an optional phone number (resets verification)."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        cc = (request.data.get("phoneCountryCode") or request.data.get("phone_country_code") or "").strip()
        num = (request.data.get("phoneNumber") or request.data.get("phone_number") or "").strip()
        user = request.user
        user.phone_country_code = cc
        user.phone_number = num
        user.is_phone_verified = False
        user.save(update_fields=["phone_country_code", "phone_number", "is_phone_verified"])
        log_security_event(SecurityEvent.Type.PHONE_ADDED, request=request, user=user)
        return Response(UserSerializer(user, context={"request": request}).data)


def _phone_cache_key(user) -> str:
    return f"phone_otp:{user.pk}"


class PhoneOtpStatusView(APIView):
    """GET /api/profile/phone/otp-status/ — tells the UI whether to show 'Send OTP'."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        provider = get_otp_provider()
        return Response({"available": provider.is_configured, "channel": provider.channel})


class PhoneVerifyRequestView(APIView):
    """POST /api/profile/phone/verify/request/ — issue an OTP via the configured provider.

    If no provider is configured (production default), returns 503 with available:false
    so the frontend keeps 'Send OTP' hidden/disabled. Phone is never auto-verified.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.phone_number:
            return Response({"detail": "Add a phone number first."}, status=status.HTTP_400_BAD_REQUEST)
        provider = get_otp_provider()
        if not provider.is_configured:
            return Response(
                {"detail": "Phone verification isn't available right now.", "available": False},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        code = f"{secrets.randbelow(900000) + 100000}"
        full_number = f"{user.phone_country_code}{user.phone_number}".strip()
        sent = provider.send_code(phone=full_number, code=code)
        if not sent:
            return Response(
                {"detail": "Couldn't send a code right now. Please try again later.", "available": True},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        # Only store the pending code once it's actually been dispatched.
        cache.set(_phone_cache_key(user), code, timeout=600)
        return Response({"detail": "Verification code sent.", "available": True})


class PhoneVerifyConfirmView(APIView):
    """POST /api/profile/phone/verify/confirm/ — confirm the OTP (only this marks verified)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        code = (request.data.get("code") or "").strip()
        expected = cache.get(_phone_cache_key(user))
        if not expected or code != expected:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(_phone_cache_key(user))
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
        return Response({"detail": "Phone verified.", "isPhoneVerified": True})


class UserProfileLookupView(APIView):
    """GET /api/users/<username_or_id>/profile/ — public profile by @username or numeric id."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, username_or_id):
        ident = (username_or_id or "").lstrip("@")
        user = None
        if ident.isdigit():
            user = User.objects.filter(pk=int(ident)).first()
        if not user:
            user = User.objects.filter(username=ident.lower()).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user, context={"request": request}).data)


class WhatsAppPreferencesView(APIView):
    """PATCH /api/profile/whatsapp-preferences/ — opt in/out (requires a phone number to opt in)."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        opt_in = request.data.get("whatsappOptIn")
        if opt_in is None:
            opt_in = request.data.get("whatsapp_opt_in")
        opt_in = bool(opt_in)
        user = request.user
        if opt_in and not user.phone_number:
            return Response({"detail": "Add a phone number before enabling WhatsApp updates."},
                            status=status.HTTP_400_BAD_REQUEST)
        user.whatsapp_opt_in = opt_in
        if opt_in:
            user.whatsapp_opt_in_at = timezone.now()
        else:
            user.whatsapp_opt_out_at = timezone.now()
        user.save(update_fields=["whatsapp_opt_in", "whatsapp_opt_in_at", "whatsapp_opt_out_at"])
        log_security_event(SecurityEvent.Type.WHATSAPP_CHANGED, request=request, user=user, opt_in=opt_in)
        return Response(UserSerializer(user, context={"request": request}).data)
