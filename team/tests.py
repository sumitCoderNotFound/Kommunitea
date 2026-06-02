from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import TeamMember


class TeamModelTests(TestCase):
    def test_str(self):
        t = TeamMember.objects.create(name="Faraz", role="tech", city="London",
                                      skills="Frontend", experience="2-3 years")
        self.assertEqual(str(t), "Faraz — Tech Team")


class TeamAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("team-list")

    def test_list_team(self):
        TeamMember.objects.create(name="Mujammil", role="tech", city="Leeds",
                                  skills="Frontend, PM", experience="7+ years")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["role_display"], "Tech Team")

    def test_filter_by_role(self):
        TeamMember.objects.create(name="Dev", role="tech", city="London",
                                  skills="Backend", experience="2-3 years")
        TeamMember.objects.create(name="Marketer", role="social", city="Stratford",
                                  skills="SEO", experience="6+ years")
        resp = self.client.get(self.url, {"role": "social"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["name"], "Marketer")
