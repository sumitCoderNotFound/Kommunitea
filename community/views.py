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
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Community, Project, ProjectScreenshot
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

    def perform_create(self, serializer):
        community = serializer.save()
        community.members.add(self.request.user)

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
    # Inherit the global CamelCase parsers (JSON + MultiPart + Form) so incoming
    # camelCase keys like techStack/rolesNeeded are converted to snake_case.

    def get_queryset(self):
        user_id = self.request.query_params.get("user")
        if user_id:
            return Project.objects.filter(owner_id=user_id).prefetch_related("screenshots")
        return Project.objects.filter(owner=self.request.user).prefetch_related("screenshots")

    def _parsed_data(self):
        """Multipart sends arrays as JSON strings; parse them so the serializer gets real lists."""
        import json
        data = {k: v for k, v in self.request.data.items()}
        for key in ("tech_stack", "links", "roles_needed"):
            val = data.get(key)
            if isinstance(val, str):
                try:
                    data[key] = json.loads(val)
                except (ValueError, TypeError):
                    data[key] = []
        # normalise the boolean from multipart strings
        if "looking_for_collaborators" in data and isinstance(data["looking_for_collaborators"], str):
            data["looking_for_collaborators"] = data["looking_for_collaborators"].lower() in ("1", "true", "yes")
        return data

    def _save_screenshots(self, project):
        shots = self.request.FILES.getlist("screenshots")
        for f in shots:
            ProjectScreenshot.objects.create(project=project, image=f)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._parsed_data())
        serializer.is_valid(raise_exception=True)
        project = serializer.save(owner=request.user)
        self._save_screenshots(project)
        out = self.get_serializer(project)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.owner_id != request.user.pk:
            raise PermissionDenied("Not your project.")
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=self._parsed_data(), partial=partial)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        # replace screenshots only if new ones were uploaded
        if request.FILES.getlist("screenshots"):
            instance.screenshots.all().delete()
            self._save_screenshots(project)
        return Response(self.get_serializer(project).data)

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.pk:
            raise PermissionDenied("Not your project.")
        instance.delete()
