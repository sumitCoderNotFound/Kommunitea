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
        RECRUITER = "recruiter", "Recruiter"

    username = None  # remove username; use email
    email = models.EmailField(unique=True)

    full_name = models.CharField(max_length=120)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
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
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Per-user streak (permanent, syncs across devices)
    streak_count = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_visit = models.DateField(null=True, blank=True)

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

    def record_visit(self):
        """Record a daily visit and update streak. Idempotent within a day."""
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()
        if self.last_visit == today:
            return  # already counted today
        if self.last_visit == today - timedelta(days=1):
            self.streak_count += 1  # consecutive day
        else:
            self.streak_count = 1  # reset / first visit
        self.last_visit = today
        if self.streak_count > self.longest_streak:
            self.longest_streak = self.streak_count
        self.save(update_fields=["streak_count", "longest_streak", "last_visit"])
        # Notify on milestone days (Duolingo-style).
        if self.streak_count in (3, 7, 14, 30, 50, 100, 365):
            try:
                from notifications.models import Notification
                Notification.push(self, self, Notification.Verb.STREAK,
                                  text=f"{self.streak_count} day streak! Keep your momentum alive.")
            except Exception:
                pass


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
