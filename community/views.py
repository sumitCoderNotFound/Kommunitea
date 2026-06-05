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

    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        """Communities the user hasn't joined yet, ranked by relevance.
        Relevance: same category as the user's interests / university match, then by member count."""
        qs = Community.objects.all()
        user = request.user
        joined_ids = set()
        if user.is_authenticated:
            joined_ids = set(user.communities_joined.values_list("id", flat=True)) if hasattr(user, "communities_joined") else set(
                Community.objects.filter(members=user).values_list("id", flat=True))
            qs = qs.exclude(id__in=joined_ids)

        from django.db.models import Count
        items = list(qs.annotate(mc=Count("members")))

        def rank(c):
            score = 0
            if user.is_authenticated:
                uni = (getattr(user, "university", "") or "").lower()
                interests = [i.lower() for i in (getattr(user, "interests", []) or [])]
                blob = f"{c.name} {c.description} {c.category}".lower()
                if uni and uni.split()[0] in blob:
                    score += 5
                if any(i in blob for i in interests):
                    score += 3
            score += min(c.mc, 50) / 50.0
            return score

        items.sort(key=rank, reverse=True)
        top = items[:8]
        return Response(CommunitySerializer(top, many=True, context={"request": request}).data)

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
