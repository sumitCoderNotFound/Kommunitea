"""Tests for username support, email/username login, and account endpoints."""
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


def reg(client, **over):
    payload = {"fullName": "Sam Lee", "username": "samlee", "email": "sam@example.com", "password": "Str0ng!Pass99"}
    payload.update(over)
    return client.post("/api/auth/register/", payload, format="json")


class UsernameRegisterTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_with_username(self):
        r = reg(self.client)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(email="sam@example.com").username, "samlee")

    def test_duplicate_username_rejected(self):
        reg(self.client)
        cache.clear()
        r = reg(self.client, email="other@example.com")  # same username
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_rejected(self):
        reg(self.client)
        cache.clear()
        r = reg(self.client, username="different")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_rules(self):
        cache.clear()
        for bad in ["ab", "has space", "admin", "bad$char"]:
            cache.clear()
            r = reg(self.client, username=bad, email=f"{abs(hash(bad))}@e.com")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, bad)

    def test_username_stored_lowercase(self):
        reg(self.client, username="SamLee2")
        self.assertTrue(User.objects.filter(username="samlee2").exists())


class LoginIdentifierTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="li@example.com", password="Str0ng!Pass99", full_name="L", username="loginname")

    def test_login_with_email(self):
        r = self.client.post("/api/auth/login/", {"email": "li@example.com", "password": "Str0ng!Pass99"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_with_username(self):
        r = self.client.post("/api/auth/login/", {"email": "loginname", "password": "Str0ng!Pass99"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)

    def test_invalid_login_generic(self):
        r = self.client.post("/api/auth/login/", {"email": "loginname", "password": "wrong"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid email/username", r.data["detail"])


class UsernameCheckTests(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(email="taken@example.com", password="Str0ng!Pass99", full_name="T", username="taken")

    def test_available(self):
        r = self.client.get("/api/auth/username/check/", {"username": "freshname"})
        self.assertTrue(r.data["available"])

    def test_taken(self):
        r = self.client.get("/api/auth/username/check/", {"username": "taken"})
        self.assertFalse(r.data["available"])

    def test_reserved(self):
        r = self.client.get("/api/auth/username/check/", {"username": "admin"})
        self.assertFalse(r.data["available"])


class AccountEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="acct@example.com", password="Old!Passw0rd99", full_name="A", username="acct")
        access = self.client.post("/api/auth/login/", {"email": "acct@example.com", "password": "Old!Passw0rd99"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_change_username(self):
        r = self.client.patch("/api/auth/username/", {"username": "newhandle"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newhandle")

    def test_change_password(self):
        r = self.client.post("/api/auth/change-password/",
                             {"currentPassword": "Old!Passw0rd99", "newPassword": "Brand!New99Pass"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand!New99Pass"))

    def test_phone_optional_and_whatsapp_requires_phone(self):
        # WhatsApp opt-in without a phone is rejected
        r = self.client.patch("/api/profile/whatsapp-preferences/", {"whatsappOptIn": True}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        # Add phone, then opt-in works
        self.client.patch("/api/profile/phone/", {"phoneCountryCode": "+44", "phoneNumber": "7700900000"}, format="json")
        r = self.client.patch("/api/profile/whatsapp-preferences/", {"whatsappOptIn": True}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.whatsapp_opt_in)
        self.assertIsNotNone(self.user.whatsapp_opt_in_at)

    def test_profile_lookup_by_username(self):
        self.client.credentials()  # public
        r = self.client.get("/api/users/acct/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["username"], "acct")

    @override_settings(OTP_PROVIDER="none")
    def test_otp_unavailable_in_production(self):
        self.client.patch("/api/profile/phone/", {"phoneCountryCode": "+44", "phoneNumber": "7700900111"}, format="json")
        status_r = self.client.get("/api/profile/phone/otp-status/")
        self.assertFalse(status_r.data["available"])
        r = self.client.post("/api/profile/phone/verify/request/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_phone_verified)

    @override_settings(OTP_PROVIDER="fake")
    def test_otp_fake_provider_flow(self):
        self.client.patch("/api/profile/phone/", {"phoneCountryCode": "+44", "phoneNumber": "7700900222"}, format="json")
        self.assertTrue(self.client.get("/api/profile/phone/otp-status/").data["available"])
        req = self.client.post("/api/profile/phone/verify/request/", {}, format="json")
        self.assertEqual(req.status_code, status.HTTP_200_OK)
        # Wrong code is rejected; phone stays unverified
        bad = self.client.post("/api/profile/phone/verify/confirm/", {"code": "000000"}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_phone_verified)
        # Correct code (read from cache, as the fake provider only logs it) verifies
        code = cache.get(f"phone_otp:{self.user.pk}")
        ok = self.client.post("/api/profile/phone/verify/confirm/", {"code": code}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_phone_verified)


class GoogleNeedsUsernameTests(APITestCase):
    def setUp(self):
        cache.clear()

    @override_settings(GOOGLE_CLIENT_ID="test-client-id")
    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_new_user_needs_username(self, mock_verify):
        mock_verify.return_value = {"email": "gx@example.com", "email_verified": True, "name": "GX", "sub": "123"}
        r = self.client.post("/api/auth/google/", {"idToken": "fake"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["needsUsername"])
        u = User.objects.get(email="gx@example.com")
        self.assertEqual(u.auth_provider, "google")
