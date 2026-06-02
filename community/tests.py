from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Member


class MemberModelTests(TestCase):
    def test_create_member(self):
        m = Member.objects.create(
            full_name="Test User", email="test@example.com", city="London",
            uk_status=Member.UKStatus.PSW, professional_field=Member.Field.SOFTWARE,
            experience=Member.Experience.MID,
        )
        self.assertEqual(str(m), "Test User (London)")
        self.assertFalse(m.is_approved)


class MemberAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("member-list")

    def test_join_community(self):
        data = {
            "full_name": "Faraz Mohammed", "email": "Faraz@Example.com",
            "city": "London", "uk_status": "student",
            "professional_field": "software", "experience": "2-3",
            "looking_for": "A job in the UK",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # email is lowercased by serializer
        self.assertEqual(Member.objects.first().email, "faraz@example.com")

    def test_duplicate_email_rejected(self):
        Member.objects.create(
            full_name="A", email="dup@example.com", city="London",
            uk_status="psw", professional_field="software", experience="2-3",
        )
        data = {
            "full_name": "B", "email": "dup@example.com", "city": "Leeds",
            "uk_status": "student", "professional_field": "data_ai", "experience": "0-1",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_requires_staff(self):
        # Member list contains PII, so it is staff-only now.
        Member.objects.create(full_name="Approved", email="a@x.com", city="London",
                              uk_status="psw", professional_field="software",
                              experience="2-3", is_approved=True)
        # anonymous -> blocked
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
        # staff -> allowed
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        U = get_user_model()
        U.objects.create_user(email="staff@x.com", password="pass1234", full_name="Staff", is_staff=True)
        tok = self.client.post(reverse("login"), {"email": "staff@x.com", "password": "pass1234"}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_missing_required_field(self):
        resp = self.client.post(self.url, {"full_name": "No Email"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
