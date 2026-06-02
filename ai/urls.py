from django.urls import path
from .views import ProfileBuilderView, CVReviewView, JobMatchView

urlpatterns = [
    path("profile-builder/", ProfileBuilderView.as_view(), name="ai-profile-builder"),
    path("cv-review/", CVReviewView.as_view(), name="ai-cv-review"),
    path("job-match/", JobMatchView.as_view(), name="ai-job-match"),
]
