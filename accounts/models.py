"""Custom user model for UK Job Tribe with full community profile."""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """User manager using email as the unique identifier (no username)."""
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Community member. Login is by email; profile fields drive the platform."""

    class Status(models.TextChoices):
        STUDENT = "student", "Current Student"
        PSW = "psw", "Post Study Work Visa"
        GRADUATE = "graduate", "Recent Graduate"
        EMPLOYED = "employed", "Employed"
        OTHER = "other", "Other"

    class Badge(models.TextChoices):
        STUDENT = "student", "Student"
        ALUMNI = "alumni", "Alumni"
        RECRUITER = "recruiter", "Recruiter"

    class UserType(models.TextChoices):
        STUDENT = "student", "Student"
        GRADUATE = "graduate", "Graduate"
        PROFESSIONAL = "professional", "Working Professional"
        JOB_SEEKER = "job_seeker", "Job Seeker"
        RECRUITER = "recruiter", "Recruiter"
        CREATOR = "creator", "Creator"
        NEWCOMER = "newcomer", "New to UK"

    username = None  # remove username; use email
    email = models.EmailField(unique=True)

    full_name = models.CharField(max_length=120)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.STUDENT)
    # Education (students/graduates)
    university = models.CharField(max_length=160, blank=True)
    course = models.CharField(max_length=160, blank=True)
    study_level = models.CharField(max_length=60, blank=True)  # e.g. Undergraduate, Masters, PhD
    graduation_date = models.CharField(max_length=20, blank=True)  # "September 2024"
    intake_year = models.CharField(max_length=10, blank=True)
    student_email = models.EmailField(blank=True)
    # Professional / Recruiter
    company = models.CharField(max_length=160, blank=True)
    job_title = models.CharField(max_length=160, blank=True)
    years_experience = models.CharField(max_length=20, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    hiring_for = models.CharField(max_length=200, blank=True)  # recruiters
    display_company = models.BooleanField(default=True)
    open_to_networking = models.BooleanField(default=True)
    open_to_referrals = models.BooleanField(default=False)
    open_to_mentoring = models.BooleanField(default=False)
    # job seeker
    target_role = models.CharField(max_length=160, blank=True)
    experience_level = models.CharField(max_length=60, blank=True)  # Entry/Mid/Senior
    job_type = models.CharField(max_length=60, blank=True)  # Full-time/Part-time/Internship
    cv_uploaded = models.BooleanField(default=False)
    # recruiter
    company_website = models.URLField(blank=True)
    # creator
    content_niche = models.CharField(max_length=120, blank=True)
    instagram = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    creator_topics = models.JSONField(default=list, blank=True)
    # newcomer / new to UK
    destination_city = models.CharField(max_length=120, blank=True)
    arrival_date = models.CharField(max_length=20, blank=True)  # "September 2025"
    newcomer_needs = models.JSONField(default=list, blank=True)  # accommodation, sim, bank, visa...
    city = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, blank=True)
    skills = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    looking_for = models.JSONField(default=list, blank=True)
    career_goals = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    portfolio = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    badge = models.CharField(max_length=20, choices=Badge.choices, blank=True)
    is_onboarded = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)  # private = follow requests need approval

    class MessagesFrom(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        FOLLOWERS = "followers", "Followers"
        CONNECTIONS = "connections", "Connections"
        NO_ONE = "no_one", "No one"

    allow_messages_from = models.CharField(max_length=16, choices=MessagesFrom.choices, default=MessagesFrom.EVERYONE)
    allow_story_sharing = models.BooleanField(default=True)
    allow_post_reshare = models.BooleanField(default=True)
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Per-user streak (permanent, syncs across devices)
    streak_count = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_visit = models.DateField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)  # presence ("online")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    def record_activity(self, activity_type="app_open"):
        """Record a meaningful daily activity and update the streak.
        Idempotent for streak purposes within a day; logs per-day activity counts
        so the consistency grid reflects real data.
        """
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()

        # Per-day activity log (real consistency history)
        day, _ = ActivityDay.objects.get_or_create(user=self, date=today)
        ActivityDay.objects.filter(pk=day.pk).update(count=models.F("count") + 1)

        if self.last_visit == today:
            return  # streak already counted today (idempotent)
        if self.last_visit == today - timedelta(days=1):
            self.streak_count += 1  # consecutive day
        else:
            self.streak_count = 1  # reset / first activity
        self.last_visit = today
        if self.streak_count > self.longest_streak:
            self.longest_streak = self.streak_count
        self.save(update_fields=["streak_count", "longest_streak", "last_visit"])
        if self.streak_count in (3, 7, 14, 30, 50, 100, 365):
            try:
                from notifications.models import Notification
                Notification.push(self, self, Notification.Verb.STREAK,
                                  text=f"{self.streak_count} day streak! Keep your momentum alive.")
            except Exception:
                pass

    # Backward-compatible alias
    def record_visit(self):
        self.record_activity("app_open")


class FollowRequest(models.Model):
    """Pending follow request for private accounts (Instagram-style)."""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_requests")
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_requests")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user.full_name} -> {self.to_user.full_name}"


class ActivityDay(models.Model):
    """One row per day a user did something — powers the real consistency grid."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_days")
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.user_id} {self.date} ({self.count})"
