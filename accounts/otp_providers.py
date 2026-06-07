"""Pluggable OTP delivery providers.

We never require SMS for signup/login. Phone verification is optional and only
runs when a provider is configured. Pick the provider via settings.OTP_PROVIDER:

    "fake"     -> FakeOtpProvider     (dev/staging; logs the code, sends nothing)
    "twilio"   -> TwilioOtpProvider   (placeholder until we pay/configure)
    "whatsapp" -> WhatsAppOtpProvider (placeholder for later)
    "none"     -> NullProvider        (production default; "Send OTP" is disabled)
"""
import logging

from django.conf import settings

logger = logging.getLogger("kommunitea.otp")


class BaseOtpProvider:
    name = "base"
    channel = "sms"  # "sms" | "whatsapp"

    @property
    def is_configured(self) -> bool:
        return False

    def send_code(self, *, phone: str, code: str) -> bool:
        """Deliver `code` to `phone`. Return True on success. Must never raise."""
        raise NotImplementedError


class NullProvider(BaseOtpProvider):
    """No provider — used in production until SMS/WhatsApp is set up."""
    name = "none"

    @property
    def is_configured(self) -> bool:
        return False

    def send_code(self, *, phone: str, code: str) -> bool:
        return False


class FakeOtpProvider(BaseOtpProvider):
    """Dev/staging only. Logs the code so testers can read it from the server logs.

    NEVER selected in production unless explicitly forced via OTP_PROVIDER=fake.
    """
    name = "fake"

    @property
    def is_configured(self) -> bool:
        return True

    def send_code(self, *, phone: str, code: str) -> bool:
        logger.warning("[FakeOtpProvider] OTP for %s is %s (dev only — not a real SMS)", phone, code)
        return True


class TwilioOtpProvider(BaseOtpProvider):
    """Placeholder. Wire up Twilio here when we're ready to pay/configure."""
    name = "twilio"

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "TWILIO_ACCOUNT_SID", "")
            and getattr(settings, "TWILIO_AUTH_TOKEN", "")
            and getattr(settings, "TWILIO_FROM_NUMBER", "")
        )

    def send_code(self, *, phone: str, code: str) -> bool:
        if not self.is_configured:
            return False
        try:
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER,
            #                         body=f"Your Kommunitea code is {code}")
            logger.error("TwilioOtpProvider.send_code not implemented yet")
            return False
        except Exception:
            logger.exception("Twilio send failed")
            return False


class WhatsAppOtpProvider(BaseOtpProvider):
    """Placeholder for WhatsApp Business / Cloud API verification, added later."""
    name = "whatsapp"
    channel = "whatsapp"

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "WHATSAPP_PHONE_ID", "")
            and getattr(settings, "WHATSAPP_TOKEN", "")
        )

    def send_code(self, *, phone: str, code: str) -> bool:
        if not self.is_configured:
            return False
        logger.error("WhatsAppOtpProvider.send_code not implemented yet")
        return False


_PROVIDERS = {
    "fake": FakeOtpProvider,
    "twilio": TwilioOtpProvider,
    "whatsapp": WhatsAppOtpProvider,
    "none": NullProvider,
}


def get_otp_provider() -> BaseOtpProvider:
    name = (getattr(settings, "OTP_PROVIDER", "none") or "none").lower()
    return _PROVIDERS.get(name, NullProvider)()
