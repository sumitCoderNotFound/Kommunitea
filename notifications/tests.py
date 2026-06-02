from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

User = get_user_model()


class NotificationTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@n.com", password="pass1234", full_name="Ann")
        self.b = User.objects.create_user(email="b@n.com", password="pass1234", full_name="Bea")
        tok = self.client.post(reverse("login"), {"email": "a@n.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_like_generates_notification_for_author(self):
        from posts.models import Post
        post = Post.objects.create(author=self.b, body="hi", category="tech")
        self.client.post(f"/api/posts/{post.id}/like/")
        # Bea logs in to see her notifications
        tok = self.client.post(reverse("login"), {"email": "b@n.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        r = self.client.get("/api/notifications/")
        self.assertEqual(r.json()["count"], 1)
        self.assertEqual(r.json()["results"][0]["verb"], "like")

    def test_unread_count_and_read_all(self):
        from notifications.models import Notification
        Notification.objects.create(recipient=self.a, actor=self.b, verb="follow")
        r = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(r.json()["count"], 1)
        self.client.post("/api/notifications/read-all/")
        r = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(r.json()["count"], 0)
