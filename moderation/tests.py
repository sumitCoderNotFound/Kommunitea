from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from posts.models import Post

User = get_user_model()


class SecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@s.com", password="pass1234", full_name="User")
        self.staff = User.objects.create_user(email="staff@s.com", password="pass1234", full_name="Staff", is_staff=True)

    def _auth(self, email):
        tok = self.client.post(reverse("login"), {"email": email, "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_non_admin_cannot_create_job(self):
        self._auth("u@s.com")
        r = self.client.post("/api/jobs/", {"title": "Dev", "company": "X", "location": "London", "applyUrl": "https://x.com"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_job(self):
        self._auth("staff@s.com")
        r = self.client.post("/api/jobs/", {"title": "Dev", "company": "X", "location": "London", "applyUrl": "https://x.com"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_non_staff_cannot_list_members(self):
        self._auth("u@s.com")
        r = self.client.get("/api/members/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_can_join_members(self):
        r = self.client.post("/api/members/", {
            "fullName": "Joiner", "email": "join@x.com", "city": "London",
            "ukStatus": "psw", "professionalField": "software", "experience": "2-3"
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)


class ReportBlockTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@b.com", password="pass1234", full_name="A")
        self.b = User.objects.create_user(email="b@b.com", password="pass1234", full_name="B")
        tok = self.client.post(reverse("login"), {"email": "a@b.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_file_report(self):
        r = self.client.post("/api/reports/", {"targetType": "post", "targetId": 1, "reason": "spam"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_block_hides_posts(self):
        Post.objects.create(author=self.b, body="hi from B", category="tech")
        # before block A sees B's post
        self.assertEqual(self.client.get("/api/posts/").json()["count"], 1)
        # block B
        self.client.post(f"/api/blocks/{self.b.id}/block/")
        self.assertEqual(self.client.get("/api/posts/").json()["count"], 0)
        # unblock
        self.client.post(f"/api/blocks/{self.b.id}/unblock/")
        self.assertEqual(self.client.get("/api/posts/").json()["count"], 1)


class FilterTests(APITestCase):
    def setUp(self):
        User.objects.create_user(email="x@f.com", password="pass1234", full_name="Dev One",
                                 university="Coventry University", city="Coventry", skills=["React", "Python"])
        User.objects.create_user(email="y@f.com", password="pass1234", full_name="Dev Two",
                                 university="Leeds", city="Leeds", skills=["Java"])
        tok = self.client.post(reverse("login"), {"email": "x@f.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_filter_by_university(self):
        r = self.client.get("/api/profiles/?university=Coventry")
        self.assertEqual(r.json()["count"], 1)

    def test_filter_by_skill(self):
        r = self.client.get("/api/profiles/?skill=React")
        self.assertEqual(r.json()["count"], 1)
