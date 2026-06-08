from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from clips.models import Clip

User = get_user_model()


def _fake_video(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42fakevideobytes", content_type="video/mp4")


class ClipTests(APITestCase):
    def setUp(self):
        self.verified = User.objects.create_user(email="v@test.com", password="pass1234", full_name="Verified")
        self.verified.is_email_verified = True
        self.verified.save()
        self.unverified = User.objects.create_user(email="u@test.com", password="pass1234", full_name="Unverified")

    def _make_clip(self, **kw):
        defaults = dict(user=self.verified, caption="hi", category=Clip.Category.UK_LIFE,
                        status=Clip.Status.READY, duration_seconds=20)
        defaults.update(kw)
        c = Clip(**defaults)
        c.video_file.save("c.mp4", _fake_video(), save=False)
        c.save()
        return c

    def test_unverified_user_cannot_upload(self):
        self.client.force_authenticate(self.unverified)
        r = self.client.post("/api/clips/", {
            "video_file": _fake_video(), "caption": "x", "category": "uk_life",
            "duration_seconds": 10, "file_size": 1000,
        }, format="multipart")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Clip.objects.count(), 0)

    def test_verified_user_can_upload(self):
        self.client.force_authenticate(self.verified)
        r = self.client.post("/api/clips/", {
            "video_file": _fake_video(), "caption": "my clip", "category": "study",
            "duration_seconds": 30, "file_size": 5000,
        }, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Clip.objects.count(), 1)
        self.assertEqual(r.data["status"], "ready")

    def test_clip_over_60s_rejected(self):
        self.client.force_authenticate(self.verified)
        r = self.client.post("/api/clips/", {
            "video_file": _fake_video(), "caption": "long", "category": "uk_life",
            "duration_seconds": 75, "file_size": 5000,
        }, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_like_save_comment_report(self):
        clip = self._make_clip()
        self.client.force_authenticate(self.unverified)
        self.assertTrue(self.client.post(f"/api/clips/{clip.id}/like/").data["is_liked"])
        self.assertTrue(self.client.post(f"/api/clips/{clip.id}/save/").data["is_saved"])
        cr = self.client.post(f"/api/clips/{clip.id}/comment/", {"body": "nice"})
        self.assertEqual(cr.status_code, 201)
        self.assertEqual(self.client.get(f"/api/clips/{clip.id}/comment/").status_code, 200)
        self.assertIn("reported", self.client.post(f"/api/clips/{clip.id}/report/", {"reason": "spam"}).data["detail"])

    def test_only_owner_deletes(self):
        clip = self._make_clip()
        self.client.force_authenticate(self.unverified)
        self.assertEqual(self.client.delete(f"/api/clips/{clip.id}/").status_code, 403)
        self.client.force_authenticate(self.verified)
        self.assertEqual(self.client.delete(f"/api/clips/{clip.id}/").status_code, 204)

    def test_private_clip_hidden_from_others(self):
        clip = self._make_clip(visibility=Clip.Visibility.PRIVATE)
        self.client.force_authenticate(self.unverified)
        self.assertEqual(self.client.get(f"/api/clips/{clip.id}/").status_code, 404)
        self.client.force_authenticate(self.verified)
        self.assertEqual(self.client.get(f"/api/clips/{clip.id}/").status_code, 200)

    def test_feed_and_explore(self):
        self._make_clip(category=Clip.Category.JOBS, caption="graduate scheme")
        self._make_clip(category=Clip.Category.STUDY)
        self.client.force_authenticate(self.verified)
        feed = self.client.get("/api/clips/feed/")
        self.assertEqual(feed.status_code, 200)
        self.assertEqual(feed.data["count"], 2)
        self.assertEqual(self.client.get("/api/clips/feed/?category=jobs").data["count"], 1)
        exp = self.client.get("/api/clips/explore/?search=graduate")
        self.assertEqual(exp.data["count"], 1)

    def test_context_action_only_with_real_data(self):
        c1 = self._make_clip(category=Clip.Category.COMMUNITY)  # no community attached
        self.client.force_authenticate(self.verified)
        data = self.client.get(f"/api/clips/{c1.id}/").data
        self.assertIsNone(data["context_action"])
