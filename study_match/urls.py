from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    StudyProfileView, GenerateView, ResultsView, ResultDetailView,
    CountriesView, CoursesView, CitiesView, UniversitiesView, CompareView,
    SavedOptionViewSet, AddToPlanView, StudyAIView,
)
from .catalog_views import (
    UniversityListView, UniversityDetailView, CourseListView, CourseDetailView,
    RecommendationsView, VerificationQueueView, UniversityUpdateView, CourseUpdateView,
    SyncUniversitiesView, SyncUkviSponsorsView, ImportCoursesCsvView, FeeBandsView, CountryInsightsView,
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
    # --- Real-data catalog (free public sources) ---
    path("catalog/universities/", UniversityListView.as_view(), name="catalog-universities"),
    path("catalog/universities/<str:pk>/", UniversityDetailView.as_view(), name="catalog-university-detail"),
    path("catalog/courses/", CourseListView.as_view(), name="catalog-courses"),
    path("catalog/courses/<str:pk>/", CourseDetailView.as_view(), name="catalog-course-detail"),
    path("catalog/recommendations/", RecommendationsView.as_view(), name="catalog-recommendations"),
    path("catalog/fee-bands/", FeeBandsView.as_view(), name="catalog-fee-bands"),
    path("catalog/countries/", CountryInsightsView.as_view(), name="catalog-countries"),
    path("insights/", CountryInsightsView.as_view(), name="catalog-insights"),
    # --- Admin verification + sync ---
    path("admin/verification-queue/", VerificationQueueView.as_view(), name="catalog-verification-queue"),
    path("admin/universities/<int:pk>/", UniversityUpdateView.as_view(), name="catalog-university-update"),
    path("admin/courses/<int:pk>/", CourseUpdateView.as_view(), name="catalog-course-update"),
    path("admin/sync/universities/", SyncUniversitiesView.as_view(), name="catalog-sync-universities"),
    path("admin/sync/ukvi-sponsors/", SyncUkviSponsorsView.as_view(), name="catalog-sync-ukvi"),
    path("admin/import/courses-csv/", ImportCoursesCsvView.as_view(), name="catalog-import-courses"),
] + router.urls
