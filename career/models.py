from django.conf import settings
from django.db import models


class CVAnalysis(models.Model):
    """A rule-based CV / ATS readiness report. The uploaded file is parsed to text
    and (optionally) deleted; only the extracted text + scores are kept."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_analyses")
    file_name = models.CharField(max_length=200, blank=True)
    extracted_text = models.TextField(blank=True)
    ats_score = models.PositiveIntegerField(default=0)
    job_match_score = models.PositiveIntegerField(null=True, blank=True)
    section_scores = models.JSONField(default=dict, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    passed_checks = models.JSONField(default=list, blank=True)
    failed_checks = models.JSONField(default=list, blank=True)
    improvement_checks = models.JSONField(default=list, blank=True)
    top_fixes = models.JSONField(default=list, blank=True)
    recommended_roles = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ReferralRequest(models.Model):
    class Status(models.TextChoices):
        NOT_REQUESTED = "not_requested", "Not requested"
        REQUESTED = "requested", "Requested"
        FOLLOW_UP = "follow_up", "Follow-up needed"
        REFERRED = "referred", "Referred"
        DECLINED = "declined", "Declined"
        NO_RESPONSE = "no_response", "No response"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_requests")
    job_application = models.ForeignKey("scheduler.JobApplication", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    company = models.CharField(max_length=160)
    role_title = models.CharField(max_length=160, blank=True)
    contact_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="referral_asks")
    contact_name = models.CharField(max_length=160, blank=True)
    contact_linkedin = models.URLField(blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_REQUESTED)
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class InterviewPrep(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_preps")
    job_application = models.ForeignKey("scheduler.JobApplication", on_delete=models.SET_NULL, null=True, blank=True, related_name="interview_preps")
    company = models.CharField(max_length=160)
    role_title = models.CharField(max_length=160, blank=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    checklist = models.JSONField(default=list, blank=True)   # [{"item": str, "done": bool}]
    questions = models.JSONField(default=list, blank=True)   # [str]
    notes = models.TextField(blank=True)
    confidence_score = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
