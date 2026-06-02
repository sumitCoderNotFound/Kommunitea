from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema
from jobs.models import Job
from . import services


@extend_schema(tags=["AI"])
class ProfileBuilderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        u = request.user
        data = {
            "full_name": u.full_name, "course": u.course, "university": u.university,
            "skills": u.skills, "career_goals": u.career_goals, "status": u.status,
        }
        # allow overrides from the request body (e.g. user tweaks before generating)
        data.update({k: v for k, v in request.data.items() if v})
        return Response(services.build_profile(data))


@extend_schema(tags=["AI"])
class CVReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        result = services.review_cv(request.data.get("cv_text") or request.data.get("cvText", ""))
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


@extend_schema(tags=["AI"])
class JobMatchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        jobs = list(Job.objects.all()[:30])
        result = services.match_jobs(request.user, jobs)
        # hydrate match job details for the frontend
        by_id = {j.id: j for j in jobs}
        for m in result.get("matches", []):
            j = by_id.get(m.get("id"))
            if j:
                m["job"] = {"id": j.id, "title": j.title, "company": j.company,
                            "location": j.location, "applyUrl": getattr(j, "apply_url", "")}
        return Response(result)
