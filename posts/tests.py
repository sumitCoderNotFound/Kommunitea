from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Post

User = get_user_model()


class PostFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="poster@test.com", password="pass1234", full_name="Poster")
        login = self.client.post(reverse("login"), {"email": "poster@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_create_and_list_post(self):
        r = self.client.post("/api/posts/", {"body": "Hiring React devs!", "category": "jobs"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.json()["author"]["fullName"], "Poster")
        r = self.client.get("/api/posts/")
        self.assertEqual(r.json()["count"], 1)

    def test_like_toggles(self):
        post = Post.objects.create(author=self.user, body="hi", category="tech")
        r = self.client.post(f"/api/posts/{post.id}/like/")
        self.assertTrue(r.json()["isLiked"])
        self.assertEqual(r.json()["likesCount"], 1)
        r = self.client.post(f"/api/posts/{post.id}/like/")
        self.assertFalse(r.json()["isLiked"])
        self.assertEqual(r.json()["likesCount"], 0)

    def test_save_toggles(self):
        post = Post.objects.create(author=self.user, body="hi", category="tech")
        r = self.client.post(f"/api/posts/{post.id}/save/")
        self.assertTrue(r.json()["isSaved"])

    def test_comment(self):
        post = Post.objects.create(author=self.user, body="hi", category="tech")
        r = self.client.post(f"/api/posts/{post.id}/comments/", {"body": "Great post!"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.json()["body"], "Great post!")

    def test_mine_filter(self):
        other = User.objects.create_user(email="other@test.com", password="pass1234", full_name="Other")
        Post.objects.create(author=self.user, body="mine", category="tech")
        Post.objects.create(author=other, body="theirs", category="tech")
        r = self.client.get("/api/posts/?mine=true")
        self.assertEqual(r.json()["count"], 1)
        self.assertEqual(r.json()["results"][0]["body"], "mine")

    def test_create_requires_auth(self):
        self.client.credentials()  # clear token
        r = self.client.post("/api/posts/", {"body": "x", "category": "tech"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class StoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="s@test.com", password="pass1234", full_name="Story User")
        login = self.client.post(reverse("login"), {"email": "s@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_stories_empty(self):
        r = self.client.get("/api/stories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_story_requires_auth_to_create(self):
        self.client.credentials()
        r = self.client.post("/api/stories/", {"caption": "hi"}, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
