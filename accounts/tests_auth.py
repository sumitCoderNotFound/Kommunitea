"""Tests for authentication hardening: verification, reset, throttling, Google, logout."""
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import (
    User, EmailVerificationToken, PasswordResetToken, SecurityEvent,
)


class RegisterVerifyTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_creates_unverified_user(self):
        r = self.client.post("/api/auth/register/", {
            "fullName": "Test User", "username": "testuser", "email": "new@example.com", "password": "Str0ng!Pass99",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        u = User.objects.get(email="new@example.com")
        self.assertFalse(u.is_email_verified)
        self.assertTrue(EmailVerificationToken.objects.filter(user=u).exists())
        self.assertTrue(SecurityEvent.objects.filter(event_type="register", email="new@example.com").exists())

    def test_email_verification_works(self):
        u = User.objects.create_user(email="v@example.com", password="Str0ng!Pass99", full_name="V")
        t = EmailVerificationToken.objects.create(user=u)
        r = self.client.post("/api/auth/email/verify/", {"token": t.token}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        u.refresh_from_db()
        self.assertTrue(u.is_email_verified)

    def test_used_or_expired_token_fails(self):
        u = User.objects.create_user(email="e@example.com", password="Str0ng!Pass99", full_name="E")
        t = EmailVerificationToken.objects.create(user=u, expires_at=timezone.now() - timezone.timedelta(hours=1))
        r = self.client.post("/api/auth/email/verify/", {"token": t.token}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_is_generic(self):
        for email in ["nobody@example.com", ""]:
            r = self.client.post("/api/auth/email/resend/", {"email": email}, format="json")
            self.assertEqual(r.status_code, status.HTTP_200_OK)
            cache.clear()  # avoid throttle across the loop

    @patch("accounts.security.send_mail", side_effect=Exception("smtp down"))
    def test_email_failure_does_not_crash_signup(self, _m):
        r = self.client.post("/api/auth/register/", {
            "fullName": "NoMail", "username": "nomail", "email": "nomail@example.com", "password": "Str0ng!Pass99",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="nomail@example.com").exists())
        self.assertIn("could not be sent", r.data["detail"])


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="reset@example.com", password="Old!Passw0rd99", full_name="R")

    def test_request_always_generic(self):
        r1 = self.client.post("/api/auth/password-reset/request/", {"email": "reset@example.com"}, format="json")
        cache.clear()
        r2 = self.client.post("/api/auth/password-reset/request/", {"email": "ghost@example.com"}, format="json")
        self.assertEqual(r1.data["detail"], r2.data["detail"])
        self.assertIn("If an account exists", r1.data["detail"])

    def test_reset_works_and_token_is_single_use(self):
        self.client.post("/api/auth/password-reset/request/", {"email": "reset@example.com"}, format="json")
        token = PasswordResetToken.objects.filter(user=self.user).latest("created_at").token
        ok = self.client.post("/api/auth/password-reset/confirm/",
                              {"token": token, "password": "Brand!New99Pass"}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand!New99Pass"))
        # reuse must fail
        again = self.client.post("/api/auth/password-reset/confirm/",
                                 {"token": token, "password": "Another!99Pass"}, format="json")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordStrengthTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_weak_passwords_rejected(self):
        for pw in ["password", "12345678", "short"]:
            cache.clear()
            r = self.client.post("/api/auth/register/", {
                "fullName": "Weak", "username": f"weak{abs(hash(pw))%100000}", "email": f"w{abs(hash(pw))}@example.com", "password": pw,
            }, format="json")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, pw)


class ThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_login_throttled(self):
        codes = []
        for _ in range(7):
            r = self.client.post("/api/auth/login/", {"email": "x@example.com", "password": "nope"}, format="json")
            codes.append(r.status_code)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, codes)


class GoogleLoginTests(APITestCase):
    def setUp(self):
        cache.clear()

    @override_settings(GOOGLE_CLIENT_ID="test-client-id")
    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_creates_and_logs_in(self, mock_verify):
        mock_verify.return_value = {"email": "g@example.com", "email_verified": True, "name": "G User"}
        r = self.client.post("/api/auth/google/", {"idToken": "fake"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        u = User.objects.get(email="g@example.com")
        self.assertTrue(u.is_email_verified)

    def test_google_unavailable_without_config(self):
        r = self.client.post("/api/auth/google/", {"idToken": "fake"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class LogoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="lo@example.com", password="Str0ng!Pass99", full_name="LO")

    def _tokens(self):
        r = self.client.post("/api/auth/login/", {"email": "lo@example.com", "password": "Str0ng!Pass99"}, format="json")
        return r.data["access"], r.data["refresh"]

    def test_logout_blacklists_refresh(self):
        access, refresh = self._tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        out = self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(out.status_code, status.HTTP_200_OK)
        # blacklisted refresh can no longer mint an access token
        r = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_all(self):
        access, _ = self._tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        out = self.client.post("/api/auth/logout-all/", {}, format="json")
        self.assertEqual(out.status_code, status.HTTP_200_OK)


class VerifiedGateTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="gate@example.com", password="Str0ng!Pass99", full_name="Gate")

    @override_settings(REQUIRE_EMAIL_VERIFICATION=True)
    def test_unverified_cannot_create_post(self):
        access = self.client.post("/api/auth/login/",
                                  {"email": "gate@example.com", "password": "Str0ng!Pass99"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        r = self.client.post("/api/posts/", {"body": "hello"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(REQUIRE_EMAIL_VERIFICATION=True)
    def test_verified_can_create_post(self):
        self.user.is_email_verified = True
        self.user.save()
        access = self.client.post("/api/auth/login/",
                                  {"email": "gate@example.com", "password": "Str0ng!Pass99"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        r = self.client.post("/api/posts/", {"body": "hello"}, format="json")
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
