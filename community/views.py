from rest_framework import mixins, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
        community = serializer.save(created_by=self.request.user)
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
        if community.created_by and community.created_by != request.user:
            from notifications.models import Notification
            Notification.push(community.created_by, request.user, Notification.Verb.LIKE,
                              text=f"joined {community.name}", target_type="community", community_id=str(community.id))
        return Response({"detail": "Joined.", "is_member": True, "members_count": community.members.count()})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        community = self.get_object()
        community.members.remove(request.user)
        return Response({"detail": "Left.", "is_member": False, "members_count": community.members.count()})

    @action(detail=True, methods=["get", "post"], url_path="posts")
    def posts(self, request, pk=None):
        """List community posts (members see all; non-members see public preview), or create one (members only)."""
        from posts.models import Post
        from posts.serializers import PostSerializer
        community = self.get_object()
        is_member = request.user.is_authenticated and community.members.filter(pk=request.user.pk).exists()
        if request.method == "GET":
            qs = community.posts.all()
            if not is_member:
                qs = qs.filter(visibility="public")  # preview for non-members
            return Response(PostSerializer(qs, many=True, context={"request": request}).data)
        # POST — create a community post
        if not is_member:
            return Response({"detail": "Join this community to post."}, status=status.HTTP_403_FORBIDDEN)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "Post cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        post = Post.objects.create(
            author=request.user, body=body, community=community,
            visibility=request.data.get("visibility", "community_only"),
            category=request.data.get("category", "university_life"),
        )
        if community.created_by and community.created_by != request.user:
            from notifications.models import Notification
            Notification.push(community.created_by, request.user, Notification.Verb.LIKE,
                              text=f"posted in {community.name}", post_id=post.id,
                              target_type="community", community_id=str(community.id))
        return Response(PostSerializer(post, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """List community members."""
        from accounts.serializers import UserSerializer
        community = self.get_object()
        users = community.members.all()[:200]
        return Response(UserSerializer(users, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"], url_path="events")
    def events(self, request, pk=None):
        """List community events, or create one (members only)."""
        from .models import CommunityEvent
        from .serializers import CommunityEventSerializer
        community = self.get_object()
        if request.method == "GET":
            return Response(CommunityEventSerializer(community.events.all(), many=True).data)
        if not community.members.filter(pk=request.user.pk).exists():
            return Response({"detail": "Join this community to add events."}, status=status.HTTP_403_FORBIDDEN)
        ser = CommunityEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ev = ser.save(community=community, created_by=request.user)
        return Response(CommunityEventSerializer(ev).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="resources")
    def resources(self, request, pk=None):
        """List community resources, or create one (members only)."""
        from .models import CommunityResource
        from .serializers import CommunityResourceSerializer
        community = self.get_object()
        if request.method == "GET":
            return Response(CommunityResourceSerializer(community.resources.all(), many=True).data)
        if not community.members.filter(pk=request.user.pk).exists():
            return Response({"detail": "Join this community to add resources."}, status=status.HTTP_403_FORBIDDEN)
        ser = CommunityResourceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        res = ser.save(community=community, created_by=request.user)
        return Response(CommunityResourceSerializer(res).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def chat(self, request, pk=None):
        """Get or create the community group chat (members only)."""
        from messaging.models import Conversation
        from messaging.serializers import ConversationSerializer
        community = self.get_object()
        if not community.members.filter(pk=request.user.pk).exists():
            return Response({"detail": "Join this community to access chat."}, status=status.HTTP_403_FORBIDDEN)
        convo = Conversation.objects.filter(community=community, kind=Conversation.Kind.COMMUNITY).first()
        if not convo:
            convo = Conversation.objects.create(kind=Conversation.Kind.COMMUNITY, title=community.name,
                                                community=community, owner=community.created_by or request.user)
        convo.participants.add(*community.members.all())
        return Response(ConversationSerializer(convo, context={"request": request}).data)


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
