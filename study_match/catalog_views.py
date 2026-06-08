"""Catalog API: universities, courses, recommendations, and admin verification."""
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import University, Course, SyncLog, SponsorStatus
from .catalog_serializers import (
    UniversitySerializer, UniversityDetailSerializer, CourseSerializer, SyncLogSerializer,
)
from .catalog_scoring import rank_courses
from .data import DISCLAIMERS


class CatalogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "pageSize"
    max_page_size = 100


def _truthy(v):
    return str(v).lower() in ("1", "true", "yes")


class UniversityListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Q
        qs = University.objects.all()
        q = request.query_params
        if q.get("search"):
            s = q["search"].strip()
            # Single-word / partial search across name, city and region.
            qs = qs.filter(Q(university_name__icontains=s) | Q(city__icontains=s) | Q(region__icontains=s))
        if q.get("city"):
            qs = qs.filter(city__icontains=q["city"])
        if q.get("region"):
            qs = qs.filter(region__iexact=q["region"])
        if q.get("country"):
            qs = qs.filter(country__iexact=q["country"])
        if q.get("russellGroup") is not None and q.get("russellGroup") != "":
            qs = qs.filter(is_russell_group=_truthy(q.get("russellGroup")))
        if q.get("sponsorStatus"):
            qs = qs.filter(ukvi_sponsor_status=q["sponsorStatus"])
        sort = q.get("sort", "name")
        qs = qs.order_by({"name": "university_name", "city": "city"}.get(sort, "university_name"))
        page = CatalogPagination()
        result = page.paginate_queryset(qs, request)
        return page.get_paginated_response(UniversitySerializer(result, many=True).data)


class UniversityDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        uni = University.objects.filter(pk=pk).first() or University.objects.filter(university_id=pk).first()
        if not uni:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = UniversityDetailSerializer(uni).data
        data["disclaimer"] = DISCLAIMERS["university"]
        return Response(data)


class CourseListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Course.objects.select_related("university").all()
        q = request.query_params
        if q.get("search"):
            qs = qs.filter(course_name__icontains=q["search"])
        if q.get("subjectArea"):
            qs = qs.filter(subject_area__iexact=q["subjectArea"])
        if q.get("university"):
            qs = qs.filter(university__university_id=q["university"])
        if q.get("city"):
            qs = qs.filter(university__city__iexact=q["city"])
        if q.get("region"):
            qs = qs.filter(university__region__iexact=q["region"])
        if q.get("studyMode"):
            qs = qs.filter(study_mode__iexact=q["studyMode"])
        if q.get("feeMax"):
            try:
                qs = qs.filter(international_fee_gbp__lte=int(q["feeMax"]))
            except ValueError:
                pass
        if q.get("feeMin"):
            try:
                qs = qs.filter(international_fee_gbp__gte=int(q["feeMin"]))
            except ValueError:
                pass
        if q.get("ieltsMax"):
            try:
                qs = qs.filter(ielts_overall__lte=float(q["ieltsMax"]))
            except ValueError:
                pass
        if q.get("placement") not in (None, ""):
            qs = qs.filter(work_placement_available=_truthy(q.get("placement")))
        if q.get("intake"):
            qs = qs.filter(intake_months__contains=q["intake"])
        page = CatalogPagination()
        result = page.paginate_queryset(qs.order_by("course_name"), request)
        return page.get_paginated_response(CourseSerializer(result, many=True).data)


class CourseDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        c = Course.objects.filter(pk=pk).first() or Course.objects.filter(course_id=pk).first()
        if not c:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = CourseSerializer(c).data
        data["disclaimer"] = DISCLAIMERS["university"]
        return Response(data)


class RecommendationsView(APIView):
    """POST: score real catalog courses against the student's inputs."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        p = {
            "desired_subject": request.data.get("desiredSubject", ""),
            "budget_gbp": request.data.get("budgetGbp"),
            "preferred_cities": request.data.get("preferredCities") or [],
            "preferred_regions": request.data.get("preferredRegions") or [],
            "qualification_level": request.data.get("qualificationLevel", ""),
            "grade_equivalent": request.data.get("gradeEquivalent", ""),
            "ielts_score": request.data.get("ieltsScore"),
            "pte_score": request.data.get("pteScore"),
            "wants_placement": bool(request.data.get("wantsPlacement")),
            "needs_scholarship": bool(request.data.get("needsScholarship")),
            "nationality": request.data.get("nationality", ""),
            "preferred_intake": request.data.get("preferredIntake", ""),
        }
        qs = Course.objects.select_related("university").all()
        if p["desired_subject"]:
            sub = p["desired_subject"]
            qs = qs.filter(course_name__icontains=sub) | qs.filter(subject_area__icontains=sub)
        ranked = rank_courses(list(qs.distinct()), p, limit=20)
        results = []
        for course, sc in ranked:
            row = CourseSerializer(course).data
            row.update({
                "matchPercentage": sc["match_percentage"], "scoreBreakdown": sc["score_breakdown"],
                "reasons": sc["reasons"], "warnings": sc["warnings"],
                "universityName": course.university.university_name,
                "city": course.university.city, "isRussellGroup": course.university.is_russell_group,
            })
            results.append(row)
        return Response({"results": results, "count": len(results), "disclaimers": DISCLAIMERS})


# ---------------- Admin (verification + sync) ----------------
class _AdminView(APIView):
    permission_classes = [permissions.IsAdminUser]


class VerificationQueueView(_AdminView):
    def get(self, request):
        unis = University.objects.filter(needs_verification=True)[:100]
        courses = Course.objects.filter(needs_verification=True)[:100]
        return Response({
            "universities": UniversitySerializer(unis, many=True).data,
            "courses": CourseSerializer(courses, many=True).data,
            "syncLogs": SyncLogSerializer(SyncLog.objects.all()[:20], many=True).data,
        })


class UniversityUpdateView(_AdminView):
    def patch(self, request, pk):
        uni = University.objects.filter(pk=pk).first()
        if not uni:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = UniversitySerializer(uni, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(last_checked_at=timezone.now())
        return Response(ser.data)


class CourseUpdateView(_AdminView):
    def patch(self, request, pk):
        c = Course.objects.filter(pk=pk).first()
        if not c:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = CourseSerializer(c, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(last_checked_at=timezone.now())
        return Response(ser.data)


class SyncUniversitiesView(_AdminView):
    def post(self, request):
        from .sync import sync_universities
        log = sync_universities(url=request.data.get("url"))
        return Response(SyncLogSerializer(log).data, status=status.HTTP_202_ACCEPTED)


class SyncUkviSponsorsView(_AdminView):
    def post(self, request):
        from .sync import sync_ukvi_sponsors
        log = sync_ukvi_sponsors(url=request.data.get("url"))
        return Response(SyncLogSerializer(log).data, status=status.HTTP_202_ACCEPTED)


class ImportCoursesCsvView(_AdminView):
    def post(self, request):
        from .sync import import_courses_csv
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Upload a CSV in the 'file' field."}, status=status.HTTP_400_BAD_REQUEST)
        log = import_courses_csv(f.read().decode("utf-8", errors="replace"))
        return Response(SyncLogSerializer(log).data, status=status.HTTP_201_CREATED)
