from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class MessagingTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@m.com", password="pass1234", full_name="Alice")
        self.b = User.objects.create_user(email="b@m.com", password="pass1234", full_name="Bob")
        tok = self.client.post(reverse("login"), {"email": "a@m.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_start_conversation_and_send(self):
        r = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        cid = r.json()["id"]
        r = self.client.post(f"/api/conversations/{cid}/messages/", {"body": "Hey Bob!"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.json()["body"], "Hey Bob!")

    def test_conversation_is_reused(self):
        r1 = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json")
        r2 = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json")
        self.assertEqual(r1.json()["id"], r2.json()["id"])

    def test_message_creates_notification(self):
        from notifications.models import Notification
        r = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json")
        self.client.post(f"/api/conversations/{r.json()['id']}/messages/", {"body": "hi"}, format="json")
        self.assertEqual(Notification.objects.filter(recipient=self.b, verb="message").count(), 1)


class MessageRequestTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@req.com", password="pass1234", full_name="AA")
        self.b = User.objects.create_user(email="b@req.com", password="pass1234", full_name="Bb")

    def _auth(self, email):
        tok = self.client.post(reverse("login"), {"email": email, "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_message_from_non_follower_is_request(self):
        # A messages B; B does not follow A -> request
        self._auth("a@req.com")
        convo = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json").json()
        self.assertTrue(convo["isRequest"])
        # B sees it in requests, not inbox
        self._auth("b@req.com")
        self.assertEqual(len(self.client.get("/api/conversations/?requests=true").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/conversations/").json()["results"]), 0)
        # B accepts
        self.client.post(f"/api/conversations/{convo['id']}/accept/")
        self.assertEqual(len(self.client.get("/api/conversations/").json()["results"]), 1)

    def test_message_from_follower_is_normal(self):
        # B follows A, so A messaging B is a normal chat
        self.b.following.add(self.a)
        self._auth("a@req.com")
        convo = self.client.post("/api/conversations/", {"userId": self.b.id}, format="json").json()
        self.assertFalse(convo["isRequest"])
