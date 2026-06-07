"""Authentication endpoints: verification, password reset, Google, logout.

Design notes:
  * Email/Google failures never crash the flow (failure isolation).
  * Reset + resend always return a generic response (no account enumeration).
  * Every meaningful event is written to SecurityEvent.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as dj_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import EmailVerificationToken, PasswordResetToken, SecurityEvent
from .security import log_security_event, send_verification_email, send_password_reset_email
from .serializers import RegisterSerializer, UserSerializer, EmailTokenObtainPairSerializer
from .throttles import (
    LoginThrottle, RegisterThrottle, PasswordResetThrottle,
    ResendVerificationThrottle, GoogleLoginThrottle,
)

logger = logging.getLogger("kommunitea.security")
User = get_user_model()
GENERIC_RESET_MSG = "If an account exists, we have sent reset instructions."


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create an unverified account + send verification."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        log_security_event(SecurityEvent.Type.REGISTER, request=request, user=user)
        # Email is failure-isolated: a send failure must not undo the signup.
        sent = send_verification_email(user, request=request)
        data = UserSerializer(user, context=self.get_serializer_context()).data
        if sent:
            return Response({**data, "detail": "Account created. Check your email to verify your address."},
                            status=status.HTTP_201_CREATED)
        return Response(
            {**data, "detail": "Account created. Verification email could not be sent. "
                               "Please resend the verification email."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — generic errors, audit logged."""
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        email = (request.data.get("email") or "").strip()
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            log_security_event(SecurityEvent.Type.LOGIN_FAILED, request=request, email=email, success=False)
            return Response({"detail": "Invalid email/username or password."}, status=status.HTTP_401_UNAUTHORIZED)
        user = getattr(serializer, "user", None)
        log_security_event(SecurityEvent.Type.LOGIN_SUCCESS, request=request, user=user, email=email)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """POST/GET /api/auth/email/verify/ — confirm an email via token."""
    permission_classes = [permissions.AllowAny]

    def _verify(self, request, token_value):
        if not token_value:
            return Response({"detail": "Missing token."}, status=status.HTTP_400_BAD_REQUEST)
        token = EmailVerificationToken.objects.filter(token=token_value).select_related("user").first()
        if not token or not token.is_valid:
            return Response({"detail": "This verification link is invalid or has expired."},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
            user = token.user
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        log_security_event(SecurityEvent.Type.EMAIL_VERIFIED, request=request, user=user)
        return Response({"detail": "Email verified. You're all set."})

    def post(self, request):
        return self._verify(request, request.data.get("token"))

    def get(self, request):
        return self._verify(request, request.query_params.get("token"))


class ResendVerificationView(APIView):
    """POST /api/auth/email/resend/ — resend verification (generic response)."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ResendVerificationThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        generic = Response({"detail": "If that account exists and is unverified, a new email is on its way."})
        if not email:
            return generic
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_email_verified:
            send_verification_email(user, request=request)
        return generic


class PasswordResetRequestView(APIView):
    """POST /api/auth/password-reset/request/ — never reveals if the email exists."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        log_security_event(SecurityEvent.Type.PASSWORD_RESET_REQUESTED, request=request, email=email)
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                send_password_reset_email(user, request=request)
        return Response({"detail": GENERIC_RESET_MSG})


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/ — single-use, expiring token."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        token_value = request.data.get("token") or ""
        new_password = request.data.get("password") or ""
        token = PasswordResetToken.objects.filter(token=token_value).select_related("user").first()
        if not token or not token.is_valid:
            return Response({"detail": "This reset link is invalid or has expired."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            dj_validate_password(new_password, user=token.user)
        except DjangoValidationError as e:
            return Response({"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            user = token.user
            user.set_password(new_password)
            user.save(update_fields=["password"])
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
        log_security_event(SecurityEvent.Type.PASSWORD_RESET_COMPLETED, request=request, user=user)
        return Response({"detail": "Password updated. You can now log in."})


class GoogleLoginView(APIView):
    """POST /api/auth/google/ — verify a Google ID token, then log in / create user."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [GoogleLoginThrottle]

    def post(self, request):
        id_token_str = request.data.get("idToken") or request.data.get("id_token") or ""
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        if not id_token_str or not client_id:
            return Response(
                {"detail": "Google sign-in is temporarily unavailable. Please use email/password."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # Guarded import + verification — any failure degrades gracefully.
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            info = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), client_id)
            email = (info.get("email") or "").strip().lower()
            if not email:
                raise ValueError("No email in Google token")
        except Exception as exc:
            logger.warning("Google login failed: %s", exc)
            log_security_event(SecurityEvent.Type.GOOGLE_LOGIN_FAILED, request=request, success=False)
            return Response(
                {"detail": "Google sign-in is temporarily unavailable. Please use email/password."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        user = User.objects.filter(email__iexact=email).first()
        created = False
        if not user:
            user = User.objects.create_user(
                email=email, password=None,
                full_name=info.get("name", "") or email.split("@")[0],
            )
            user.set_unusable_password()
            user.auth_provider = User.AuthProvider.GOOGLE
            created = True
        else:
            # Existing email account now also linked to Google.
            if user.auth_provider == User.AuthProvider.EMAIL:
                user.auth_provider = User.AuthProvider.BOTH
        if not user.google_id:
            user.google_id = str(info.get("sub", ""))
        if info.get("email_verified") and not user.is_email_verified:
            user.is_email_verified = True
        user.save()

        refresh = RefreshToken.for_user(user)
        log_security_event(SecurityEvent.Type.GOOGLE_LOGIN_SUCCESS, request=request, user=user, created=created)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "needsUsername": not bool(user.username),
        })


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklist the supplied refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh") or ""
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            pass  # already invalid/expired — logout is idempotent
        log_security_event(SecurityEvent.Type.LOGOUT, request=request, user=request.user)
        return Response({"detail": "Logged out."})


class LogoutAllView(APIView):
    """POST /api/auth/logout-all/ — blacklist every outstanding refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for t in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=t)
        except Exception:
            logger.exception("logout-all failed")
        log_security_event(SecurityEvent.Type.LOGOUT_ALL, request=request, user=request.user)
        return Response({"detail": "Logged out of all devices."})
