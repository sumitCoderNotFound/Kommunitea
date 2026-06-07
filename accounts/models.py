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

    email = models.EmailField(unique=True)
    # Public handle (separate from email). Nullable so existing users + new
    # Google users without a chosen handle remain valid.
    username = models.CharField(max_length=30, unique=True, null=True, blank=True, db_index=True)
    is_email_verified = models.BooleanField(default=False)

    class AuthProvider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"
        BOTH = "both", "Both"

    auth_provider = models.CharField(max_length=10, choices=AuthProvider.choices, default=AuthProvider.EMAIL)
    google_id = models.CharField(max_length=64, blank=True, db_index=True)

    full_name = models.CharField(max_length=120)
    display_name = models.CharField(max_length=120, blank=True)

    # Optional phone / WhatsApp (never required at signup)
    phone_country_code = models.CharField(max_length=6, blank=True)   # e.g. +44
    phone_number = models.CharField(max_length=20, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    whatsapp_opt_in = models.BooleanField(default=False)
    whatsapp_opt_in_at = models.DateTimeField(null=True, blank=True)
    whatsapp_opt_out_at = models.DateTimeField(null=True, blank=True)

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
    def profile_completion(self) -> int:
        """Rough completeness score (0-100) used by the profile completion card."""
        checks = [
            bool(self.avatar),
            bool(self.bio),
            bool(self.city or self.university or self.company),
            bool(self.skills),
            bool(self.phone_number),
            bool(self.is_email_verified),
            bool(self.career_goals or self.target_role),
            bool(self.username),
        ]
        return round(100 * sum(checks) / len(checks))

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


class Favourite(models.Model):
    """A user's favourite person / community / post (for the Home 'Favourites' feed)."""
    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        COMMUNITY = "community", "Community"
        POST = "post", "Post"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="favourites")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    target_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "kind", "target_id")
        ordering = ["-created_at"]


class Highlight(models.Model):
    """A profile highlight (e.g. UK Life / Jobs / Visa) - a labelled circle on the profile."""
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="highlights")
    title = models.CharField(max_length=40)
    icon = models.CharField(max_length=40, blank=True)   # ionicon name
    cover_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]


# --- Authentication & security ---
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings as dj_settings


def _gen_token() -> str:
    return secrets.token_urlsafe(48)


class EmailVerificationToken(models.Model):
    """Single-use, expiring token emailed to a user to verify their address."""
    user = models.ForeignKey(dj_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_tokens")
    token = models.CharField(max_length=128, unique=True, default=_gen_token, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class PasswordResetToken(models.Model):
    """Single-use, expiring token for password reset."""
    user = models.ForeignKey(dj_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=128, unique=True, default=_gen_token, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class SecurityEvent(models.Model):
    """Audit log for authentication-related events."""
    class Type(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN_SUCCESS = "login_success", "Login success"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGOUT = "logout", "Logout"
        LOGOUT_ALL = "logout_all", "Logout all devices"
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password reset requested"
        PASSWORD_RESET_COMPLETED = "password_reset_completed", "Password reset completed"
        EMAIL_VERIFIED = "email_verified", "Email verified"
        EMAIL_VERIFICATION_SENT = "email_verification_sent", "Verification email sent"
        GOOGLE_LOGIN_SUCCESS = "google_login_success", "Google login success"
        GOOGLE_LOGIN_FAILED = "google_login_failed", "Google login failed"
        RATE_LIMITED = "rate_limited", "Rate limited"
        PHONE_ADDED = "phone_added", "Phone number added"
        WHATSAPP_CHANGED = "whatsapp_changed", "WhatsApp opt-in changed"
        USERNAME_CHANGED = "username_changed", "Username changed"
        PASSWORD_CHANGED = "password_changed", "Password changed"

    user = models.ForeignKey(dj_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_events")
    email = models.EmailField(blank=True)
    event_type = models.CharField(max_length=40, choices=Type.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)
    success = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "created_at"]), models.Index(fields=["email"])]

    def __str__(self):
        return f"{self.event_type} {self.email} {'ok' if self.success else 'fail'}"
