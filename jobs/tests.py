from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Job


class JobModelTests(TestCase):
    def test_str(self):
        j = Job.objects.create(title="Backend Dev", company="Acme",
                               location="London", apply_url="https://x.com")
        self.assertEqual(str(j), "Backend Dev @ Acme")


class JobAPITests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client = APIClient()
        self.url = reverse("job-list")
        U = get_user_model()
        U.objects.create_user(email="staff@j.com", password="pass1234", full_name="Staff", is_staff=True)
        tok = self.client.post(reverse("login"), {"email": "staff@j.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_create_and_list_job(self):
        data = {"title": "React Dev", "company": "Tech Ltd", "location": "Remote UK",
                "job_type": "full_time", "visa_sponsorship": True,
                "apply_url": "https://apply.example.com"}
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["count"], 1)

    def test_inactive_jobs_hidden(self):
        Job.objects.create(title="Old", company="X", location="London",
                           apply_url="https://x.com", is_active=False)
        Job.objects.create(title="New", company="Y", location="Leeds",
                           apply_url="https://y.com", is_active=True)
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["count"], 1)

    def test_filter_visa_sponsorship(self):
        Job.objects.create(title="Sponsored", company="X", location="London",
                           apply_url="https://x.com", visa_sponsorship=True)
        Job.objects.create(title="No Visa", company="Y", location="Leeds",
                           apply_url="https://y.com", visa_sponsorship=False)
        resp = self.client.get(self.url, {"visa_sponsorship": "true"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["title"], "Sponsored")
