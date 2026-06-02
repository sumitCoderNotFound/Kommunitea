from rest_framework import mixins, viewsets, permissions
from drf_spectacular.utils import extend_schema
from .models import Member
from .serializers import MemberSerializer


@extend_schema(tags=["Community"])
class MemberViewSet(mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """Join the community (POST) and list approved members (GET)."""
    serializer_class = MemberSerializer
    def get_permissions(self):
        # Anyone can join (POST). Browsing the member list/details is staff-only,
        # since it contains emails and challenges (PII).
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    filterset_fields = ["uk_status", "professional_field", "experience", "city"]
    search_fields = ["full_name", "city", "looking_for"]

    def get_queryset(self):
        qs = Member.objects.all()
        # Public list only shows approved members; full list needs ?all=true
        if self.action == "list" and self.request.query_params.get("all") != "true":
            qs = qs.filter(is_approved=True)
        return qs
