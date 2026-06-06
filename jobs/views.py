from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from config.permissions import IsAdminOrReadOnly
from drf_spectacular.utils import extend_schema
from .models import Job
from .serializers import JobSerializer


@extend_schema(tags=["Jobs"])
class JobViewSet(viewsets.ModelViewSet):
    """Job board: anyone can read; only staff/moderators can create, update, delete."""
    serializer_class = JobSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["job_type", "visa_sponsorship", "location", "is_active"]
    search_fields = ["title", "company", "location", "description"]

    def get_permissions(self):
        if self.action in ["save_job", "apply_job"]:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def _upsert_application(self, request, job, status_value):
        """Create or update the user's tracked application for this job (deduped by user+job)."""
        from scheduler.models import JobApplication
        from django.utils import timezone
        defaults = {
            "company": job.company, "role_title": job.title,
            "job_link": job.apply_url, "source": "Job board", "status": status_value,
        }
        app, created = JobApplication.objects.get_or_create(user=request.user, job=job, defaults=defaults)
        if not created:
            # Don't downgrade an applied item back to saved; otherwise update status.
            if not (status_value == "saved" and app.status != "saved"):
                app.status = status_value
        if status_value == "applied" and not app.applied_date:
            app.applied_date = timezone.localdate()
        app.save()
        from scheduler.serializers import JobApplicationSerializer
        return JobApplicationSerializer(app, context={"request": request}).data, created

    @action(detail=True, methods=["post"], url_path="save")
    def save_job(self, request, pk=None):
        data, created = self._upsert_application(request, self.get_object(), "saved")
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="apply")
    def apply_job(self, request, pk=None):
        job = self.get_object()
        data, created = self._upsert_application(request, job, "applied")
        return Response({**data, "applyUrl": job.apply_url}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def get_queryset(self):
        qs = Job.objects.all()
        if self.action == "list" and self.request.query_params.get("all") != "true":
            qs = qs.filter(is_active=True)
        return qs
