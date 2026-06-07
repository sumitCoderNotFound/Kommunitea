from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from scheduler.models import Task
from study_match.models import StudyMatchResult, SavedStudyOption

User = get_user_model()


class StudyMatchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="sm@example.com", password="StrongPass123", full_name="SM User", username="smuser")
        self.client.force_authenticate(self.user)

    def _profile_payload(self, **over):
        data = {
            "currentCountry": "India", "educationLevel": "Bachelor's",
            "currentQualification": "BTech Computer Science", "subjectInterest": "Computer Science",
            "careerGoal": "Software Engineer", "desiredStudyLevel": "Masters",
            "preferredCountries": ["UK", "Canada", "Germany"],
            "needsScholarship": True, "priorities": ["low_cost", "strong_job_market", "post_study_work"],
        }
        data.update(over)
        return data

    def test_profile_create_and_get(self):
        r = self.client.post("/api/study-match/profile/", self._profile_payload(), format="json")
        self.assertIn(r.status_code, (200, 201))
        g = self.client.get("/api/study-match/profile/")
        self.assertEqual(g.data["subject_interest"], "Computer Science")

    def test_generate_produces_scored_result(self):
        self.client.post("/api/study-match/profile/", self._profile_payload(), format="json")
        r = self.client.post("/api/study-match/generate/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r.data["overall_summary"])
        countries = r.data["country_scores"]
        self.assertTrue(any(c["country"] == "UK" for c in countries))
        for c in countries:
            self.assertGreaterEqual(c["score"], 0)
            self.assertLessEqual(c["score"], 100)
        self.assertTrue(r.data["course_recommendations"])
        self.assertTrue(r.data["city_recommendations"])
        self.assertIn("study", r.data["disclaimers"])
        self.assertEqual(StudyMatchResult.objects.filter(user=self.user).count(), 1)

    def test_results_list_and_detail(self):
        self.client.post("/api/study-match/profile/", self._profile_payload(), format="json")
        gen = self.client.post("/api/study-match/generate/", {}, format="json")
        rid = gen.data["id"]
        self.assertEqual(self.client.get("/api/study-match/results/").status_code, 200)
        d = self.client.get(f"/api/study-match/results/{rid}/")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(d.data["id"], rid)

    def test_reference_endpoints_public(self):
        self.client.logout()
        for path in ("countries", "courses", "cities"):
            self.assertEqual(self.client.get(f"/api/study-match/{path}/").status_code, 200)

    def test_compare_countries(self):
        r = self.client.post("/api/study-match/compare/", {"countries": ["UK", "Canada", "USA"]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["comparison"]), 3)

    def test_save_option_and_list(self):
        r = self.client.post("/api/study-match/saved/", {
            "optionType": "university", "title": "University of Manchester", "city": "Manchester",
            "course": "Computer Science", "status": "shortlisted",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(SavedStudyOption.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.client.get("/api/study-match/saved/?type=university").status_code, 200)

    def test_add_to_plan_creates_scheduler_tasks(self):
        before = Task.objects.filter(user=self.user).count()
        r = self.client.post("/api/study-match/add-to-plan/", {
            "category": "university",
            "tasks": [{"title": "Shortlist 5 universities"}, {"title": "Prepare SOP"}],
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["created"], 2)
        self.assertEqual(Task.objects.filter(user=self.user, source_ref="studymatch").count(), 2)
        self.assertEqual(Task.objects.filter(user=self.user).count(), before + 2)

    def test_ai_fallback_without_key(self):
        self.client.post("/api/study-match/profile/", self._profile_payload(), format="json")
        self.client.post("/api/study-match/generate/", {}, format="json")
        r = self.client.post("/api/study-match/ai/", {"intent": "next_steps"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["source"], "rule_based")
        self.assertTrue(r.data["answer"])
