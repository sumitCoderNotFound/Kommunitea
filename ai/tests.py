from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from jobs.models import Job

User = get_user_model()


class AIFeatureTests(APITestCase):
    """These exercise the non-AI fallback path (no API key in CI), proving the
    feature works for MVP even before a key is added."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="ai@k.com", password="pass1234", full_name="AI User",
            course="MSc Computer Science", university="Coventry University",
            skills=["React", "Python"], interests=["AI"], looking_for=["jobs"],
            career_goals="Land a graduate developer role")
        tok = self.client.post(reverse("login"), {"email": "ai@k.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_profile_builder(self):
        r = self.client.post("/api/ai/profile-builder/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("bio", r.json())
        self.assertTrue(len(r.json()["bio"]) > 10)
        self.assertIn("aiPowered", r.json())

    def test_cv_review_requires_text(self):
        r = self.client.post("/api/ai/cv-review/", {"cvText": "too short"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cv_review_returns_feedback(self):
        cv = ("John Doe john@example.com\nExperience: Built a web app with React and Django, "
              "led a team of 3, improved load time by 40%. Education: MSc Computer Science.")
        r = self.client.post("/api/ai/cv-review/", {"cvText": cv}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        body = r.json()
        self.assertIn("strengths", body)
        self.assertIn("improvements", body)
        self.assertIn("atsTips", body)

    def test_job_match(self):
        Job.objects.create(title="Graduate React Developer", company="TechCo",
                           location="London", description="Looking for React and Python skills",
                           apply_url="https://x.com")
        r = self.client.post("/api/ai/job-match/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        matches = r.json()["matches"]
        self.assertTrue(len(matches) >= 1)
        self.assertIn("job", matches[0])  # hydrated job details
