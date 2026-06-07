"""Study Match data models."""
from django.conf import settings
from django.db import models


class StudyProfile(models.Model):
    """The user's study-abroad inputs (one per user, updatable)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_profile")
    # Step 1 — about you
    current_country = models.CharField(max_length=80, blank=True)
    education_level = models.CharField(max_length=80, blank=True)
    current_qualification = models.CharField(max_length=160, blank=True)
    marks_or_cgpa = models.CharField(max_length=40, blank=True)
    work_experience = models.CharField(max_length=80, blank=True)
    # Step 2 — study goal
    desired_study_level = models.CharField(max_length=40, blank=True)
    subject_interest = models.CharField(max_length=120, blank=True)
    career_goal = models.CharField(max_length=160, blank=True)
    preferred_intake = models.CharField(max_length=40, blank=True)
    preferred_countries = models.JSONField(default=list, blank=True)
    # Step 3 — budget
    tuition_budget = models.CharField(max_length=40, blank=True)
    living_budget = models.CharField(max_length=40, blank=True)
    needs_scholarship = models.BooleanField(default=False)
    needs_part_time_work = models.BooleanField(default=False)
    # Step 4 — english / requirements
    english_test_type = models.CharField(max_length=40, blank=True)
    english_test_score = models.CharField(max_length=40, blank=True)
    passport_status = models.BooleanField(default=False)
    document_status = models.BooleanField(default=False)
    # Step 5 — priorities (list of keys)
    priorities = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"StudyProfile<{self.user_id}>"


class StudyMatchResult(models.Model):
    """A generated result snapshot (kept so users can revisit past matches)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_results")
    study_profile = models.ForeignKey(StudyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="results")
    overall_summary = models.TextField(blank=True)
    country_scores = models.JSONField(default=list, blank=True)
    course_recommendations = models.JSONField(default=list, blank=True)
    university_recommendations = models.JSONField(default=list, blank=True)
    city_recommendations = models.JSONField(default=list, blank=True)
    career_market_insights = models.JSONField(default=dict, blank=True)
    visa_cost_checklist = models.JSONField(default=dict, blank=True)
    action_plan = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SavedStudyOption(models.Model):
    class OptionType(models.TextChoices):
        COUNTRY = "country", "Country"
        COURSE = "course", "Course"
        UNIVERSITY = "university", "University"
        CITY = "city", "City"
        SCHOLARSHIP = "scholarship", "Scholarship"
        ACCOMMODATION = "accommodation", "Accommodation"

    class Status(models.TextChoices):
        RESEARCHING = "researching", "Researching"
        SHORTLISTED = "shortlisted", "Shortlisted"
        APPLIED = "applied", "Applied"
        OFFER = "offer_received", "Offer received"
        REJECTED = "rejected", "Rejected"
        ACCEPTED = "accepted", "Accepted"
        VISA = "visa_stage", "Visa stage"
        ACCOMMODATION = "accommodation_stage", "Accommodation stage"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_study_options")
    option_type = models.CharField(max_length=20, choices=OptionType.choices)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    university = models.CharField(max_length=160, blank=True)
    course = models.CharField(max_length=160, blank=True)
    fee = models.CharField(max_length=80, blank=True)
    intake = models.CharField(max_length=40, blank=True)
    entry_requirements = models.TextField(blank=True)
    english_requirement = models.CharField(max_length=120, blank=True)
    official_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RESEARCHING)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class StudyTask(models.Model):
    """A Study Match task; can be mirrored into the main Plan (scheduler.Task)."""
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        DONE = "done", "Done"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_tasks")
    saved_option = models.ForeignKey(SavedStudyOption, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.TODO)
    linked_plan_task_id = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class StudySource(models.Model):
    """Official/external sources surfaced in Study Match (for transparency)."""
    source_name = models.CharField(max_length=120)
    source_url = models.URLField()
    source_type = models.CharField(max_length=40, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.source_name
