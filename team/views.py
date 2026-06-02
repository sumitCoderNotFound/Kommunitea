from rest_framework import viewsets
from drf_spectacular.utils import extend_schema
from .models import TeamMember
from .serializers import TeamMemberSerializer


@extend_schema(tags=["Team"])
class TeamMemberViewSet(viewsets.ModelViewSet):
    """Showcase the core team building UK Job Tribe."""
    serializer_class = TeamMemberSerializer
    filterset_fields = ["role", "is_active"]
    search_fields = ["name", "skills", "city"]

    def get_queryset(self):
        qs = TeamMember.objects.all()
        if self.action == "list" and self.request.query_params.get("all") != "true":
            qs = qs.filter(is_active=True)
        return qs
