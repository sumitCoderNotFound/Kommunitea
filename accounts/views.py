from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema
from .models import FollowRequest
from .filters import ProfileFilter
from notifications.models import Notification
from .serializers import RegisterSerializer, UserSerializer, EmailTokenObtainPairSerializer

User = get_user_model()


@extend_schema(tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create an account."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=["Auth"])
class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — returns {access, refresh} JWT tokens."""
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=["Auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — the current user's profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Profiles"])
class ProfileViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """Profiles: view others, update your own (/me), follow/unfollow, avatar."""
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-created_at")
    filterset_class = ProfileFilter
    search_fields = ["full_name", "university", "skills", "city"]

    def get_queryset(self):
        # Don't show the current user in the browse/search list (they can't follow themselves).
        qs = User.objects.all().order_by("-created_at")
        if self.action == "list" and self.request.user.is_authenticated:
            qs = qs.exclude(pk=self.request.user.pk)
        return qs

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        if request.method == "PATCH":
            ser = self.get_serializer(request.user, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
            return Response(ser.data)
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=["patch"], url_path="me/avatar",
            parser_classes=[MultiPartParser, FormParser])
    def avatar(self, request):
        user = request.user
        user.avatar = request.data.get("avatar")
        user.save()
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"])
    def follow(self, request, pk=None):
        target = self.get_object()
        if target == request.user:
            return Response({"detail": "You cannot follow yourself."},
                            status=status.HTTP_400_BAD_REQUEST)
        if target.is_private:
            # private account -> create a pending request
            FollowRequest.objects.get_or_create(from_user=request.user, to_user=target)
            Notification.push(target, request.user, Notification.Verb.REQUEST)
            return Response({"detail": "Request sent.", "status": "requested"})
        request.user.following.add(target)
        Notification.push(target, request.user, Notification.Verb.FOLLOW)
        return Response({"detail": "Following.", "status": "following"})

    @action(detail=True, methods=["post"])
    def unfollow(self, request, pk=None):
        target = self.get_object()
        request.user.following.remove(target)
        FollowRequest.objects.filter(from_user=request.user, to_user=target).delete()
        return Response({"detail": "Unfollowed.", "status": "none"})

    @action(detail=False, methods=["get"], url_path="requests")
    def requests(self, request):
        """Incoming follow requests for the current (private) user."""
        reqs = request.user.received_requests.select_related("from_user")
        data = [{
            "id": r.id,
            "from_user": UserSerializer(r.from_user, context={"request": request}).data,
            "created_at": r.created_at,
        } for r in reqs]
        return Response(data)

    @action(detail=True, methods=["post"], url_path="accept-request")
    def accept_request(self, request, pk=None):
        """Accept a pending request from user pk."""
        fr = FollowRequest.objects.filter(from_user_id=pk, to_user=request.user).first()
        if not fr:
            return Response({"detail": "No request."}, status=status.HTTP_404_NOT_FOUND)
        fr.from_user.following.add(request.user)
        Notification.push(fr.from_user, request.user, Notification.Verb.FOLLOW, text="accepted your follow request")
        fr.delete()
        return Response({"detail": "Accepted."})

    @action(detail=True, methods=["post"], url_path="reject-request")
    def reject_request(self, request, pk=None):
        FollowRequest.objects.filter(from_user_id=pk, to_user=request.user).delete()
        return Response({"detail": "Rejected."})


# ---- Streak (per-user, permanent) ----
from rest_framework.views import APIView


class StreakView(APIView):
    """GET returns current streak; POST records today's visit and returns updated streak."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            "current_streak": u.streak_count,
            "longest_streak": u.longest_streak,
            "last_visit": u.last_visit,
        })

    def post(self, request):
        u = request.user
        u.record_visit()
        return Response({
            "current_streak": u.streak_count,
            "longest_streak": u.longest_streak,
            "last_visit": u.last_visit,
        })


# ---- Skills suggestions via ESCO (with curated fallback) ----
import json as _json
from urllib.request import urlopen, Request as _Req
from urllib.parse import urlencode as _enc

_FALLBACK_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js", "Django", "SQL",
    "Java", "C++", "Data Analysis", "Machine Learning", "Excel", "Communication",
    "Project Management", "Leadership", "Teamwork", "Problem Solving", "Marketing",
    "Figma", "UI Design", "Public Speaking", "Writing", "Git", "AWS", "Docker",
]


class SkillSuggestView(APIView):
    """GET /api/skills/suggest/?q=python -> {results: [..]} from ESCO, fallback to curated."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response({"results": _FALLBACK_SKILLS[:12]})
        try:
            params = _enc({"text": q, "language": "en", "type": "skill", "limit": 8})
            url = f"https://ec.europa.eu/esco/api/suggest2?{params}"
            req = _Req(url, headers={"Accept": "application/json", "User-Agent": "Kommunitea"})
            with urlopen(req, timeout=4) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            results = [r.get("title") for r in data.get("_embedded", {}).get("results", []) if r.get("title")]
            if results:
                return Response({"results": results})
        except Exception:
            pass
        # fallback: filter curated list by query
        ql = q.lower()
        matches = [s for s in _FALLBACK_SKILLS if ql in s.lower()]
        return Response({"results": matches or _FALLBACK_SKILLS[:12]})


# ---- GDPR: export my data + delete my account ----
class MyDataExportView(APIView):
    """GET /api/auth/my-data/ -> a JSON bundle of everything we hold on the user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        u = request.user
        data = {
            "account": UserSerializer(u, context={"request": request}).data,
            "posts": list(u.posts.values("id", "body", "category", "created_at")) if hasattr(u, "posts") else [],
            "exported_at": __import__("django").utils.timezone.now().isoformat(),
            "note": "This is a copy of the personal data Kommunitea holds about you.",
        }
        return Response(data)


class DeleteAccountView(APIView):
    """DELETE /api/auth/delete-account/ -> permanently delete the user and their data."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        u = request.user
        u.delete()  # cascades to posts/messages/etc. via FK on_delete
        return Response({"detail": "Your account and data have been deleted."}, status=status.HTTP_200_OK)
