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
from accounts.views import RegisterView, LoginView, MeView, ProfileViewSet
from posts.views import PostViewSet, StoryViewSet
from messaging.views import ConversationViewSet
from notifications.views import NotificationViewSet
from moderation.views import ReportViewSet, BlockViewSet
from community.views import MemberViewSet
from jobs.views import JobViewSet
from team.views import TeamMemberViewSet

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")
router.register(r"stories", StoryViewSet, basename="story")
router.register(r"conversations", ConversationViewSet, basename="conversation")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"reports", ReportViewSet, basename="report")
router.register(r"blocks", BlockViewSet, basename="block")
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"members", MemberViewSet, basename="member")
router.register(r"jobs", JobViewSet, basename="job")
router.register(r"team", TeamMemberViewSet, basename="team")

urlpatterns = [
    path("api/ai/", include("ai.urls")),
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    # API
    path("api/", include(router.urls)),
    # Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
