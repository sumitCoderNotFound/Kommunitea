from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AuthFlowTests(APITestCase):
    def test_register_login_me(self):
        # Register
        r = self.client.post(reverse("register"), {
            "fullName": "Faraz Mohammed", "email": "faraz@test.com", "password": "Str0ng!Pass99",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        # Login -> JWT
        r = self.client.post(reverse("login"), {
            "email": "faraz@test.com", "password": "Str0ng!Pass99",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        token = r.data["access"]

        # Me (authenticated)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.get(reverse("me"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # camelCase field present
        self.assertEqual(r.json()["fullName"], "Faraz Mohammed")
        self.assertFalse(r.json()["isOnboarded"])

    def test_me_requires_auth(self):
        r = self.client.get(reverse("me"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_onboarding_update(self):
        User.objects.create_user(email="a@test.com", password="pass1234", full_name="A")
        login = self.client.post(reverse("login"), {"email": "a@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        r = self.client.patch(reverse("me"), {
            "university": "Coventry University", "course": "MSc CS",
            "skills": ["React", "Python"], "lookingFor": ["jobs"], "isOnboarded": True,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.json()["isOnboarded"])
        self.assertEqual(r.json()["skills"], ["React", "Python"])


class FollowTests(APITestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(email="u1@test.com", password="pass1234", full_name="User One")
        self.u2 = User.objects.create_user(email="u2@test.com", password="pass1234", full_name="User Two")
        login = self.client.post(reverse("login"), {"email": "u1@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_follow_and_unfollow(self):
        r = self.client.post(f"/api/profiles/{self.u2.id}/follow/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.u2.followers.count(), 1)
        r = self.client.post(f"/api/profiles/{self.u2.id}/unfollow/")
        self.assertEqual(self.u2.followers.count(), 0)

    def test_cannot_follow_self(self):
        r = self.client.post(f"/api/profiles/{self.u1.id}/follow/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class PrivacyAndRequestTests(APITestCase):
    def setUp(self):
        self.priv = User.objects.create_user(email="priv@test.com", password="pass1234",
                                              full_name="Private User", is_private=True)
        self.pub = User.objects.create_user(email="pub@test.com", password="pass1234",
                                             full_name="Public User", is_private=False)
        self.me = User.objects.create_user(email="me@test.com", password="pass1234", full_name="Me")
        login = self.client.post(reverse("login"), {"email": "me@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_follow_public_is_instant(self):
        r = self.client.post(f"/api/profiles/{self.pub.id}/follow/")
        self.assertEqual(r.json()["status"], "following")
        self.assertEqual(self.pub.followers.count(), 1)

    def test_follow_private_creates_request(self):
        r = self.client.post(f"/api/profiles/{self.priv.id}/follow/")
        self.assertEqual(r.json()["status"], "requested")
        self.assertEqual(self.priv.followers.count(), 0)
        self.assertEqual(self.priv.received_requests.count(), 1)

    def test_accept_request(self):
        # me requests to follow priv
        self.client.post(f"/api/profiles/{self.priv.id}/follow/")
        # priv logs in and accepts
        login = self.client.post(reverse("login"), {"email": "priv@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        r = self.client.post(f"/api/profiles/{self.me.id}/accept-request/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.priv.followers.count(), 1)

    def test_search_by_name(self):
        r = self.client.get("/api/profiles/?search=Public")
        names = [u["fullName"] for u in r.json()["results"]]
        self.assertIn("Public User", names)
