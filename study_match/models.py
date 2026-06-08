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
    match_score = models.PositiveIntegerField(null=True, blank=True)
    source_name = models.CharField(max_length=160, blank=True)
    source_url = models.URLField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
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


# ============================================================================
# UK university & course CATALOG (free-public-data discovery + matching).
# Every record carries source_url, last_checked_at, data_confidence and
# needs_verification. Unknown facts are stored as NULL — never invented.
# ============================================================================

class DataConfidence(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class SponsorStatus(models.TextChoices):
    LICENSED = "licensed", "Licensed sponsor"
    NOT_LISTED = "not_listed", "Not on register"
    UNKNOWN = "unknown", "Unknown / not checked"


class University(models.Model):
    university_id = models.SlugField(max_length=120, unique=True)
    university_name = models.CharField(max_length=200, db_index=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    region = models.CharField(max_length=120, blank=True, db_index=True)
    country = models.CharField(max_length=80, default="United Kingdom")
    website_url = models.URLField(blank=True)
    ukprn = models.CharField(max_length=20, blank=True, db_index=True)
    postcode = models.CharField(max_length=16, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    university_type = models.CharField(max_length=80, blank=True)
    is_russell_group = models.BooleanField(default=False)
    ukvi_sponsor_status = models.CharField(max_length=16, choices=SponsorStatus.choices, default=SponsorStatus.UNKNOWN)
    sponsor_rating = models.CharField(max_length=40, blank=True)
    international_office_url = models.URLField(blank=True)
    accommodation_url = models.URLField(blank=True)
    scholarship_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    data_confidence = models.CharField(max_length=8, choices=DataConfidence.choices, default=DataConfidence.LOW)
    needs_verification = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["university_name"]

    def __str__(self):
        return self.university_name


class Course(models.Model):
    course_id = models.SlugField(max_length=160, unique=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="courses")
    university_name = models.CharField(max_length=200, blank=True)  # denormalised for fast lists
    course_name = models.CharField(max_length=240, db_index=True)
    degree_level = models.CharField(max_length=60, blank=True, db_index=True)
    subject_area = models.CharField(max_length=120, blank=True, db_index=True)
    duration = models.CharField(max_length=60, blank=True)
    study_mode = models.CharField(max_length=60, blank=True)
    intake_months = models.JSONField(default=list, blank=True)
    international_fee_gbp = models.PositiveIntegerField(null=True, blank=True)
    international_fee_text = models.CharField(max_length=120, blank=True)
    home_fee_gbp = models.PositiveIntegerField(null=True, blank=True)
    application_fee_gbp = models.PositiveIntegerField(null=True, blank=True)
    entry_requirements = models.TextField(blank=True)
    english_language_requirement = models.CharField(max_length=200, blank=True)
    ielts_overall = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    ielts_per_component = models.CharField(max_length=120, blank=True)
    pte_requirement = models.CharField(max_length=80, blank=True)
    work_placement_available = models.BooleanField(null=True, blank=True)
    scholarship_info = models.TextField(blank=True)
    campus_location = models.CharField(max_length=160, blank=True)
    course_url = models.URLField(blank=True)
    application_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    fee_verified = models.BooleanField(default=False)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    data_confidence = models.CharField(max_length=8, choices=DataConfidence.choices, default=DataConfidence.LOW)
    needs_verification = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course_name"]

    def __str__(self):
        return f"{self.course_name} — {self.university_name}"


class DataSource(models.Model):
    source_name = models.CharField(max_length=120, unique=True)
    source_type = models.CharField(max_length=60, blank=True)
    source_url = models.URLField(blank=True)
    update_frequency = models.CharField(max_length=60, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=40, default="idle")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.source_name


class SyncLog(models.Model):
    source_name = models.CharField(max_length=120)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_records = models.PositiveIntegerField(default=0)
    inserted_records = models.PositiveIntegerField(default=0)
    updated_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=40, default="running")
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]


# ============================================================================
# Country intelligence + shared import-run log (auto-refresh system).
# Scores are DERIVED/curated indicative signals, not official statistics.
# ============================================================================

class StudyDataImportRun(models.Model):
    """Shared log for every Study Match import/refresh job."""
    source_name = models.CharField(max_length=120)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="running")  # running/success/failed/skipped
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source_name} · {self.status} · {self.started_at:%Y-%m-%d %H:%M}"


class CountryStudyInsight(models.Model):
    country = models.CharField(max_length=40, unique=True)   # code/key e.g. "UK"
    name = models.CharField(max_length=80)
    study_score = models.PositiveIntegerField(default=0)
    work_score = models.PositiveIntegerField(default=0)
    budget_score = models.PositiveIntegerField(default=0)
    visa_score = models.PositiveIntegerField(default=0)
    language_score = models.PositiveIntegerField(default=0)
    ranking_score = models.PositiveIntegerField(default=0)
    student_life_score = models.PositiveIntegerField(default=0)
    overall_score = models.PositiveIntegerField(default=0)
    best_for_subjects = models.JSONField(default=list, blank=True)
    popular_cities = models.JSONField(default=list, blank=True)
    tuition_band = models.CharField(max_length=20, blank=True)
    living_cost_band = models.CharField(max_length=20, blank=True)
    post_study_work_summary = models.CharField(max_length=200, blank=True)
    part_time_work_summary = models.CharField(max_length=200, blank=True)
    language_notes = models.CharField(max_length=200, blank=True)
    risk_notes = models.TextField(blank=True)
    weekly_update_summary = models.TextField(blank=True)
    source_name = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    update_frequency = models.CharField(max_length=20, default="monthly")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-overall_score"]

    def __str__(self):
        return self.name


# ============================================================================
# City data pipeline: raw source tables → clean CityStudyData master → API.
# Signals are indicative bands (curated/derived), never invented exact numbers.
# ============================================================================

class _RawImport(models.Model):
    """Base for source-specific raw import tables (keeps source history)."""
    source_url = models.URLField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-imported_at"]


class RawGovStudentSponsorData(_RawImport): pass
class RawONSRentData(_RawImport): pass
class RawNomisLabourData(_RawImport): pass
class RawAdzunaJobsData(_RawImport): pass
class RawPoliceSafetyData(_RawImport): pass
class RawHesaProviderData(_RawImport): pass


class CityStudyData(models.Model):
    city = models.CharField(max_length=120, db_index=True)
    slug = models.SlugField(max_length=140, unique=True)
    region = models.CharField(max_length=120, blank=True, db_index=True)
    country = models.CharField(max_length=80, default="United Kingdom")
    cost_level = models.CharField(max_length=20, blank=True)            # Low/Medium/Medium-high/High/Very high
    rent_level = models.CharField(max_length=20, blank=True)
    monthly_living_cost_band = models.CharField(max_length=40, blank=True)  # indicative band text
    average_rent_band = models.CharField(max_length=40, blank=True)
    salary_signal = models.CharField(max_length=20, blank=True)
    employment_signal = models.CharField(max_length=20, blank=True)
    part_time_job_signal = models.CharField(max_length=20, blank=True)  # Limited/Moderate/Strong/Very strong
    graduate_job_market_signal = models.CharField(max_length=20, blank=True)
    safety_signal = models.CharField(max_length=20, blank=True)         # Low risk/Moderate/Higher caution
    student_life_signal = models.CharField(max_length=20, blank=True)
    international_community_signal = models.CharField(max_length=20, blank=True)
    accommodation_difficulty = models.CharField(max_length=20, blank=True)  # Easy/Moderate/Hard
    transport_signal = models.CharField(max_length=20, blank=True)
    main_industries = models.JSONField(default=list, blank=True)
    best_for_subjects = models.JSONField(default=list, blank=True)
    best_for_career_areas = models.JSONField(default=list, blank=True)
    top_universities = models.JSONField(default=list, blank=True)       # derived from catalog
    related_communities = models.JSONField(default=list, blank=True)
    city_summary = models.TextField(blank=True)
    why_choose_this_city = models.TextField(blank=True)
    what_to_be_careful_about = models.TextField(blank=True)
    # internal numeric signals (0-5) used to derive the match score; not shown raw
    cost_value = models.PositiveIntegerField(default=3)
    rent_value = models.PositiveIntegerField(default=3)
    part_time_value = models.PositiveIntegerField(default=3)
    grad_value = models.PositiveIntegerField(default=3)
    student_life_value = models.PositiveIntegerField(default=3)
    community_value = models.PositiveIntegerField(default=3)
    accommodation_value = models.PositiveIntegerField(default=3)
    overall_city_score = models.PositiveIntegerField(default=0)
    source_name = models.CharField(max_length=160, blank=True)
    source_url = models.URLField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    data_confidence = models.CharField(max_length=12, choices=DataConfidence.choices, default=DataConfidence.LOW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-overall_city_score", "city"]

    def __str__(self):
        return self.city


class ExternalJob(models.Model):
    title = models.CharField(max_length=240)
    company = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    country = models.CharField(max_length=80, default="United Kingdom")
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    job_type = models.CharField(max_length=60, blank=True)
    category = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=60, blank=True)
    apply_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_checked_at"]

    def __str__(self):
        return f"{self.title} — {self.company}"
