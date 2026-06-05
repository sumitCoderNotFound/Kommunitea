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


from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Community, Project
from .serializers import CommunitySerializer, ProjectSerializer


@extend_schema(tags=["Communities"])
class CommunityViewSet(viewsets.ModelViewSet):
    """Browse/join communities. ?mine=true lists communities the user joined."""
    serializer_class = CommunitySerializer
    filterset_fields = ["category"]
    search_fields = ["name", "description"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Community.objects.all()
        if self.request.query_params.get("mine") == "true" and self.request.user.is_authenticated:
            qs = qs.filter(members=self.request.user)
        return qs

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        community = self.get_object()
        community.members.add(request.user)
        return Response({"detail": "Joined.", "is_member": True, "members_count": community.members.count()})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        community = self.get_object()
        community.members.remove(request.user)
        return Response({"detail": "Left.", "is_member": False, "members_count": community.members.count()})


@extend_schema(tags=["Projects"])
class ProjectViewSet(viewsets.ModelViewSet):
    """User showcase projects. ?user=<id> lists a given user's projects; default = mine."""
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user_id = self.request.query_params.get("user")
        if user_id:
            return Project.objects.filter(owner_id=user_id)
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_object(self):
        obj = super().get_object()
        return obj

    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Not your project.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Not your project.")
        instance.delete()
