from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from study_match.models import University, Course, SponsorStatus

User = get_user_model()


class CatalogTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_studymatch_catalog")

    def setUp(self):
        self.user = User.objects.create_user(email="cat@example.com", password="StrongPass123", full_name="Cat", username="catuser")
        self.admin = User.objects.create_user(email="adm@example.com", password="StrongPass123", full_name="Adm", username="admuser", is_staff=True)

    def test_seed_facts(self):
        self.assertEqual(University.objects.count(), 40)
        self.assertEqual(University.objects.filter(is_russell_group=True).count(), 24)
        ucl = University.objects.get(university_id="university-college-london")
        self.assertTrue(ucl.is_russell_group)
        self.assertEqual(ucl.city, "London")
        # Honest defaults: sponsor unknown, needs verification, no invented data.
        self.assertEqual(ucl.ukvi_sponsor_status, SponsorStatus.UNKNOWN)
        self.assertTrue(ucl.needs_verification)

    def test_universities_list_pagination_and_filters(self):
        r = self.client.get("/api/study-match/catalog/universities/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)
        self.assertEqual(r.data["count"], 40)
        rg = self.client.get("/api/study-match/catalog/universities/?russellGroup=true")
        self.assertEqual(rg.data["count"], 24)
        london = self.client.get("/api/study-match/catalog/universities/?city=London")
        self.assertTrue(london.data["count"] >= 5)
        search = self.client.get("/api/study-match/catalog/universities/?search=manchester")
        self.assertTrue(search.data["count"] >= 1)

    def test_university_detail_with_courses(self):
        uni = University.objects.get(university_id="university-of-manchester")
        Course.objects.create(course_id="uom-msc-cs", university=uni, university_name=uni.university_name,
                              course_name="MSc Computer Science", subject_area="Computer Science", degree_level="Masters")
        r = self.client.get(f"/api/study-match/catalog/universities/{uni.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["courses"]), 1)
        self.assertIn("disclaimer", r.data)

    def test_recommendations_scoring_and_warnings(self):
        uni = University.objects.get(university_id="university-of-leeds")
        # Missing fee + unknown sponsor → partial budget + warnings, never invented.
        Course.objects.create(course_id="leeds-msc-ds", university=uni, university_name=uni.university_name,
                              course_name="MSc Data Science", subject_area="Data Science", degree_level="Masters")
        self.client.force_authenticate(self.user)
        r = self.client.post("/api/study-match/catalog/recommendations/", {
            "desiredSubject": "Data Science", "budgetGbp": 20000, "preferredCities": ["Leeds"],
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["results"])
        top = r.data["results"][0]
        self.assertIn("matchPercentage", top)
        self.assertIn("scoreBreakdown", top)
        self.assertTrue(any("fee" in w.lower() for w in top["warnings"]))
        self.assertTrue(any("sponsor" in w.lower() for w in top["warnings"]))

    def test_csv_course_import(self):
        from study_match.sync import import_courses_csv
        csv_text = (
            "course_name,university_name,degree_level,subject_area,international_fee_gbp,ielts_overall,source_url\n"
            "MSc Cyber Security,University of Birmingham,Masters,Cyber Security,28000,6.5,https://www.birmingham.ac.uk\n"
            "MSc Ghost,Nonexistent University,Masters,Other,,,\n"
        )
        log = import_courses_csv(csv_text)
        self.assertEqual(log.inserted_records, 1)
        self.assertEqual(log.failed_records, 1)  # unknown university is skipped, not invented
        c = Course.objects.get(course_name="MSc Cyber Security")
        self.assertEqual(c.international_fee_gbp, 28000)
        self.assertFalse(c.fee_verified)  # imported data still needs manual verification

    def test_admin_verification_queue_requires_staff(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/study-match/admin/verification-queue/").status_code, 403)
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/study-match/admin/verification-queue/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("universities", r.data)
