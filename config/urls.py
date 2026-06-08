"""URL configuration for UK Job Tribe backend."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)
from accounts.views import MeView, ProfileViewSet, StreakView, SkillSuggestView, MyDataExportView, DeleteAccountView
from accounts.auth_views import (
    RegisterView, LoginView, VerifyEmailView, ResendVerificationView,
    PasswordResetRequestView, PasswordResetConfirmView, GoogleLoginView,
    LogoutView, LogoutAllView,
)
from accounts.account_views import (
    UsernameCheckView, UsernameUpdateView, ChangePasswordView,
    PhoneUpdateView, PhoneVerifyRequestView, PhoneVerifyConfirmView, PhoneOtpStatusView,
    WhatsAppPreferencesView, UserProfileLookupView,
)
from posts.views import PostViewSet, StoryViewSet
from messaging.views import ConversationViewSet
from notifications.views import NotificationViewSet, RunRemindersView
from moderation.views import ReportViewSet, BlockViewSet
from community.views import MemberViewSet, CommunityViewSet, ProjectViewSet
from jobs.views import JobViewSet, SponsorCompanyViewSet
from career.views import CVAnalysisViewSet, ReferralRequestViewSet, InterviewPrepViewSet
from accounts.career_views import FavouriteViewSet, HighlightViewSet
from team.views import TeamMemberViewSet
from scheduler.views import TaskViewSet, WeeklyGoalViewSet, OpportunityListView, SchedulerOverviewView, JobApplicationViewSet
from external_shares.views import ExternalShareViewSet
from clips.views import ClipViewSet, UserClipsView

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")
router.register(r"stories", StoryViewSet, basename="story")
router.register(r"conversations", ConversationViewSet, basename="conversation")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"reports", ReportViewSet, basename="report")
router.register(r"blocks", BlockViewSet, basename="block")
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"members", MemberViewSet, basename="member")
router.register(r"communities", CommunityViewSet, basename="community")
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"jobs", JobViewSet, basename="job")
router.register(r"career-tools/sponsor-companies", SponsorCompanyViewSet, basename="sponsor-company")
router.register(r"cv", CVAnalysisViewSet, basename="cv")
router.register(r"referrals", ReferralRequestViewSet, basename="referral")
router.register(r"interview-prep", InterviewPrepViewSet, basename="interview-prep")
router.register(r"favourites", FavouriteViewSet, basename="favourite")
router.register(r"highlights", HighlightViewSet, basename="highlight")
router.register(r"team", TeamMemberViewSet, basename="team")
router.register(r"scheduler/tasks", TaskViewSet, basename="task")
router.register(r"scheduler/goals", WeeklyGoalViewSet, basename="weeklygoal")
router.register(r"scheduler/applications", JobApplicationViewSet, basename="jobapplication")
router.register(r"external-shares", ExternalShareViewSet, basename="external-share")
router.register(r"clips", ClipViewSet, basename="clip")

urlpatterns = [
    path("api/users/<int:user_id>/clips/", UserClipsView.as_view({"get": "by_user"}), name="user-clips"),
    path("api/communities/<int:community_id>/clips/", UserClipsView.as_view({"get": "by_community"}), name="community-clips"),
    path("api/ai/", include("ai.urls")),
    path("api/study-match/", include("study_match.urls")),
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    # Email verification
    path("api/auth/email/verify/", VerifyEmailView.as_view(), name="email-verify"),
    path("api/auth/email/resend/", ResendVerificationView.as_view(), name="email-resend"),
    # Password reset
    path("api/auth/password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("api/auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # Google + logout
    path("api/auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_alias"),
    # Username + password management
    path("api/auth/username/check/", UsernameCheckView.as_view(), name="username-check"),
    path("api/auth/username/", UsernameUpdateView.as_view(), name="username-update"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    # Optional phone + WhatsApp
    path("api/profile/phone/", PhoneUpdateView.as_view(), name="profile-phone"),
    path("api/profile/phone/otp-status/", PhoneOtpStatusView.as_view(), name="phone-otp-status"),
    path("api/profile/phone/verify/request/", PhoneVerifyRequestView.as_view(), name="phone-verify-request"),
    path("api/profile/phone/verify/confirm/", PhoneVerifyConfirmView.as_view(), name="phone-verify-confirm"),
    path("api/profile/whatsapp-preferences/", WhatsAppPreferencesView.as_view(), name="whatsapp-preferences"),
    # Public profile by @username or id
    path("api/users/<str:username_or_id>/profile/", UserProfileLookupView.as_view(), name="user-profile-lookup"),
    path("api/streak/", StreakView.as_view(), name="streak"),
    path("api/streak/touch/", StreakView.as_view(), name="streak-touch"),
    path("api/scheduler/opportunities/", OpportunityListView.as_view(), name="opportunities"),
    path("api/scheduler/overview/", SchedulerOverviewView.as_view(), name="scheduler-overview"),
    path("api/auth/my-data/", MyDataExportView.as_view(), name="my-data"),
    path("api/auth/delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("api/skills/suggest/", SkillSuggestView.as_view(), name="skill-suggest"),
    # API
    path("api/career-tools/sponsorship-jobs/", JobViewSet.as_view({"get": "list"}), name="sponsorship-jobs"),
    path("api/cron/run-reminders/", RunRemindersView.as_view(), name="run-reminders"),
    path("api/", include(router.urls)),
    # Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
