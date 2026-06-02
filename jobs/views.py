from rest_framework import viewsets
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

    def get_queryset(self):
        qs = Job.objects.all()
        if self.action == "list" and self.request.query_params.get("all") != "true":
            qs = qs.filter(is_active=True)
        return qs
