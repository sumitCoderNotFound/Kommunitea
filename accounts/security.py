"""Auth/security helpers: audit logging, failure-isolated email, token issuance."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import EmailVerificationToken, PasswordResetToken, SecurityEvent

logger = logging.getLogger("kommunitea.security")


def client_ip(request) -> str | None:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_security_event(event_type, *, request=None, user=None, email="", success=True, **metadata):
    """Write a SecurityEvent. Never raises — logging must not break the flow."""
    try:
        SecurityEvent.objects.create(
            user=user if (user and getattr(user, "pk", None)) else None,
            email=(email or (getattr(user, "email", "") if user else "")) or "",
            event_type=event_type,
            ip_address=client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT", "")[:400] if request else ""),
            success=success,
            metadata=metadata or {},
        )
    except Exception:  # pragma: no cover - audit logging must never crash a request
        logger.exception("Failed to write SecurityEvent %s", event_type)


def _frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _safe_send(subject: str, message: str, to_email: str) -> bool:
    """Send an email; return True on success, False on failure (never raises)."""
    try:
        send_mail(
            subject, message,
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@kommunitea.app"),
            [to_email], fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Email send failed to %s", to_email)
        return False


def send_verification_email(user, request=None) -> bool:
    """Issue a verification token and email it. Returns whether the email sent."""
    token = EmailVerificationToken.objects.create(user=user)
    link = f"{_frontend_url()}/verify-email?token={token.token}"
    sent = _safe_send(
        "Verify your Kommunitea email",
        f"Hi {user.full_name or 'there'},\n\nConfirm your email to activate your account:\n{link}\n\n"
        "This link expires in 48 hours. If you didn't sign up, ignore this email.",
        user.email,
    )
    log_security_event(SecurityEvent.Type.EMAIL_VERIFICATION_SENT, request=request, user=user, success=sent)
    return sent


def send_password_reset_email(user, request=None) -> bool:
    token = PasswordResetToken.objects.create(user=user)
    link = f"{_frontend_url()}/reset-password?token={token.token}"
    return _safe_send(
        "Reset your Kommunitea password",
        f"Hi {user.full_name or 'there'},\n\nReset your password here:\n{link}\n\n"
        "This link expires in 1 hour and can be used once. If you didn't request this, ignore this email.",
        user.email,
    )
