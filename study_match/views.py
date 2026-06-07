"""Study Match API views. Phase 1 logic; Phase 2/4 degrade gracefully."""
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEmailVerified
from .models import StudyProfile, StudyMatchResult, SavedStudyOption
from .serializers import (
    StudyProfileSerializer, StudyMatchResultSerializer, SavedStudyOptionSerializer,
)
from . import engine
from .data import COUNTRIES, UK_CITIES, COURSES, DISCLAIMERS, OFFICIAL_SOURCES
from .providers import get_jobs_provider
from .ai import ai_assistant


def _get_profile(user):
    return StudyProfile.objects.filter(user=user).first()


class StudyProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        p = _get_profile(request.user)
        if not p:
            return Response({}, status=status.HTTP_200_OK)
        return Response(StudyProfileSerializer(p).data)

    def post(self, request):
        p = _get_profile(request.user)
        ser = StudyProfileSerializer(p, data=request.data, partial=bool(p))
        ser.is_valid(raise_exception=True)
        ser.save(user=request.user)
        return Response(ser.data, status=status.HTTP_200_OK if p else status.HTTP_201_CREATED)

    def patch(self, request):
        return self.post(request)


class GenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = _get_profile(request.user)
        if not profile:
            # Allow generating from a posted profile in one shot.
            ser = StudyProfileSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            profile = ser.save(user=request.user)
        elif request.data:
            ser = StudyProfileSerializer(profile, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            profile = ser.save()
        data = engine.generate_result(profile, jobs_provider=get_jobs_provider())
        result = StudyMatchResult.objects.create(
            user=request.user, study_profile=profile,
            overall_summary=data["overall_summary"], country_scores=data["country_scores"],
            course_recommendations=data["course_recommendations"],
            university_recommendations=data["university_recommendations"],
            city_recommendations=data["city_recommendations"],
            career_market_insights=data["career_market_insights"],
            visa_cost_checklist=data["visa_cost_checklist"], action_plan=data["action_plan"],
        )
        out = StudyMatchResultSerializer(result).data
        out["disclaimers"] = DISCLAIMERS
        return Response(out, status=status.HTTP_201_CREATED)


class ResultsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = StudyMatchResult.objects.filter(user=request.user)[:20]
        return Response(StudyMatchResultSerializer(qs, many=True).data)


class ResultDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        r = StudyMatchResult.objects.filter(user=request.user, pk=pk).first()
        if not r:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        out = StudyMatchResultSerializer(r).data
        out["disclaimers"] = DISCLAIMERS
        return Response(out)


# --- Reference data (public-ish, read-only) ---
class CountriesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"countries": COUNTRIES, "disclaimers": DISCLAIMERS, "sources": OFFICIAL_SOURCES})


class CoursesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"courses": COURSES, "disclaimers": DISCLAIMERS})


class CitiesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"cities": UK_CITIES, "disclaimers": DISCLAIMERS})


class UniversitiesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = _get_profile(request.user)
        course_key = engine.match_course_key(getattr(profile, "subject_interest", "") or request.query_params.get("course", "")) if profile else request.query_params.get("course")
        return Response({"universities": engine.recommend_universities(profile or StudyProfile(user=request.user), course_key),
                         "disclaimer": DISCLAIMERS["university"]})


class CompareView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        keys = request.data.get("countries") or list(COUNTRIES.keys())
        keys = [k for k in keys if k in COUNTRIES]
        profile = _get_profile(request.user) or StudyProfile(user=request.user)
        course_key = engine.match_course_key(getattr(profile, "subject_interest", "") or "")
        rows = [engine.score_country(k, profile, course_key) for k in keys]
        return Response({"comparison": rows, "disclaimers": DISCLAIMERS})


class SavedOptionViewSet(viewsets.ModelViewSet):
    serializer_class = SavedStudyOptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SavedStudyOption.objects.filter(user=self.request.user)
        t = self.request.query_params.get("type")
        return qs.filter(option_type=t) if t else qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddToPlanView(APIView):
    """Mirror Study Match tasks/deadlines into the main Plan (scheduler.Task)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from scheduler.models import Task
        items = request.data.get("tasks") or []
        category = request.data.get("category", "university")
        valid_cats = {c.value for c in Task.Category}
        if category not in valid_cats:
            category = Task.Category.OTHER
        created = 0
        for it in items:
            title = (it.get("title") if isinstance(it, dict) else str(it)) or ""
            if not title.strip():
                continue
            Task.objects.create(
                user=request.user, title=title.strip()[:200],
                notes=(it.get("description", "") if isinstance(it, dict) else ""),
                category=category, source=Task.Source.MANUAL, source_ref="studymatch",
            )
            created += 1
        return Response({"created": created}, status=status.HTTP_201_CREATED)


class StudyAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        intent = request.data.get("intent", "explain_result")
        question = request.data.get("question", "")
        result = StudyMatchResult.objects.filter(user=request.user).first()
        return Response(ai_assistant(intent, result, question))
