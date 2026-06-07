from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    StudyProfileView, GenerateView, ResultsView, ResultDetailView,
    CountriesView, CoursesView, CitiesView, UniversitiesView, CompareView,
    SavedOptionViewSet, AddToPlanView, StudyAIView,
)

router = DefaultRouter()
router.register(r"saved", SavedOptionViewSet, basename="study-saved")

urlpatterns = [
    path("profile/", StudyProfileView.as_view(), name="study-profile"),
    path("generate/", GenerateView.as_view(), name="study-generate"),
    path("results/", ResultsView.as_view(), name="study-results"),
    path("results/<int:pk>/", ResultDetailView.as_view(), name="study-result-detail"),
    path("countries/", CountriesView.as_view(), name="study-countries"),
    path("courses/", CoursesView.as_view(), name="study-courses"),
    path("universities/", UniversitiesView.as_view(), name="study-universities"),
    path("cities/", CitiesView.as_view(), name="study-cities"),
    path("compare/", CompareView.as_view(), name="study-compare"),
    path("add-to-plan/", AddToPlanView.as_view(), name="study-add-to-plan"),
    path("ai/", StudyAIView.as_view(), name="study-ai"),
] + router.urls
