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

    @action(detail=True, methods=["get"])
    def followers(self, request, pk=None):
        """Users who follow this profile (optional ?search=)."""
        target = self.get_object()
        qs = target.followers.all()
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(full_name__icontains=search) | Q(university__icontains=search) | Q(course__icontains=search))
        data = UserSerializer(qs, many=True, context={"request": request}).data
        return Response(data)

    @action(detail=True, methods=["get"])
    def following(self, request, pk=None):
        """Users this profile follows (optional ?search=)."""
        target = self.get_object()
        qs = target.following.all()
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(full_name__icontains=search) | Q(university__icontains=search) | Q(course__icontains=search))
        data = UserSerializer(qs, many=True, context={"request": request}).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="me/active-nearby")
    def active_nearby(self, request):
        """Members from the same university who are active now (presence within 2 min)."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Q
        user = request.user
        cutoff = timezone.now() - timedelta(minutes=2)
        qs = User.objects.filter(last_seen__gte=cutoff).exclude(pk=user.pk)
        scope = "everyone"
        if user.university:
            uni_qs = qs.filter(university__iexact=user.university)
            if uni_qs.exists():
                qs = uni_qs
                scope = "university"
        elif user.city:
            city_qs = qs.filter(city__iexact=user.city)
            if city_qs.exists():
                qs = city_qs
                scope = "city"
        sample = qs[:6]
        return Response({
            "count": qs.count(),
            "scope": scope,
            "where": user.university if scope == "university" else (user.city if scope == "city" else ""),
            "users": UserSerializer(sample, many=True, context={"request": request}).data,
        })

    @action(detail=False, methods=["patch"], url_path="me/cover",
            parser_classes=[MultiPartParser, FormParser])
    def update_cover(self, request):
        """Upload a cover banner image for the current user."""
        user = request.user
        if "cover_image" in request.FILES:
            user.cover_image = request.FILES["cover_image"]
            user.save(update_fields=["cover_image"])
        return Response(UserSerializer(user, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="me/analytics")
    def my_analytics(self, request):
        """Career analytics derived from real scheduler tasks + streak."""
        from scheduler.models import Task
        u = request.user
        tasks = Task.objects.filter(user=u)
        applications = tasks.filter(category="job_deadline").count()
        interviews = tasks.filter(category="interview").count()
        referrals = tasks.filter(category="referral_followup").count()
        networking = tasks.filter(category="networking").count()
        completed = tasks.filter(completed=True).count()
        # Career score blends profile completeness, streak, and activity.
        profile_bits = sum([bool(u.avatar), bool(u.bio), bool(u.university), len(u.skills or []) > 0, u.following.exists()])
        score = round((profile_bits / 5) * 40 + min(u.streak_count * 3, 20) + min(completed * 2, 20) + min((applications + interviews) * 2, 20))
        return Response({
            "applications": applications,
            "interviews": interviews,
            "referrals": referrals,
            "networking": networking,
            "completed_tasks": completed,
            "career_score": min(score, 100),
        })

    @action(detail=False, methods=["get"], url_path="me/achievements")
    def my_achievements(self, request):
        """Duolingo-style achievements derived from real signals."""
        u = request.user
        from posts.models import Post
        posts_count = Post.objects.filter(author=u).count()
        followers = u.followers.count()
        following = u.following.count()
        streak = u.streak_count
        longest = u.longest_streak
        skills = len(u.skills or [])
        profile_bits = sum([bool(u.avatar), bool(u.bio), bool(u.university), skills > 0, following > 0])
        defs = [
            {"key": "first_post", "title": "First Post", "icon": "create", "desc": "Share your first post", "earned": posts_count >= 1, "progress": min(posts_count, 1), "target": 1},
            {"key": "prolific", "title": "Prolific", "icon": "albums", "desc": "Publish 10 posts", "earned": posts_count >= 10, "progress": min(posts_count, 10), "target": 10},
            {"key": "streak_3", "title": "Getting Started", "icon": "flame", "desc": "3 day streak", "earned": longest >= 3, "progress": min(longest, 3), "target": 3},
            {"key": "streak_7", "title": "On Fire", "icon": "flame", "desc": "7 day streak", "earned": longest >= 7, "progress": min(longest, 7), "target": 7},
            {"key": "streak_30", "title": "Unstoppable", "icon": "flame", "desc": "30 day streak", "earned": longest >= 30, "progress": min(longest, 30), "target": 30},
            {"key": "networker", "title": "Networker", "icon": "people", "desc": "Follow 10 people", "earned": following >= 10, "progress": min(following, 10), "target": 10},
            {"key": "popular", "title": "Popular", "icon": "star", "desc": "Reach 10 followers", "earned": followers >= 10, "progress": min(followers, 10), "target": 10},
            {"key": "skilled", "title": "Skilled", "icon": "ribbon", "desc": "Add 5 skills", "earned": skills >= 5, "progress": min(skills, 5), "target": 5},
            {"key": "complete", "title": "All Set", "icon": "checkmark-done", "desc": "Complete your profile", "earned": profile_bits >= 5, "progress": profile_bits, "target": 5},
        ]
        return Response({"achievements": defs, "earned_count": sum(1 for d in defs if d["earned"]), "total": len(defs)})

    @action(detail=False, methods=["get"], url_path="me/replies")
    def my_replies(self, request):
        """Comments the current user has written (the 'Replies' activity tab)."""
        from posts.models import Comment
        from posts.serializers import CommentSerializer
        qs = Comment.objects.filter(author=request.user).select_related("post").order_by("-created_at")[:50]
        data = [{
            "id": c.id,
            "body": c.body,
            "post_id": c.post_id,
            "created_at": c.created_at,
        } for c in qs]
        return Response(data)


# ---- Streak (per-user, permanent) ----
from rest_framework.views import APIView


class StreakView(APIView):
    """GET returns full streak data; POST records a meaningful activity and returns it."""
    permission_classes = [permissions.IsAuthenticated]

    def _payload(self, u):
        from datetime import timedelta
        from django.utils import timezone
        from accounts.models import ActivityDay
        today = timezone.localdate()
        # last 90 days of real activity (consistency history)
        since = today - timedelta(days=89)
        rows = {a.date: a.count for a in u.activity_days.filter(date__gte=since)}
        history = [{"date": (since + timedelta(days=i)).isoformat(), "count": rows.get(since + timedelta(days=i), 0)}
                   for i in range(90)]
        # this week's activity Mon..Sun
        monday = today - timedelta(days=today.weekday())
        week_activity = [bool(rows.get(monday + timedelta(days=i), 0)) for i in range(7)]
        return {
            "current_streak": u.streak_count,
            "longest_streak": u.longest_streak,
            "last_activity_date": u.last_visit.isoformat() if u.last_visit else None,
            "has_checked_in_today": u.last_visit == today,
            "activities_today": rows.get(today, 0),
            "week_activity": week_activity,
            "history": history,
        }

    def get(self, request):
        return Response(self._payload(request.user))

    def post(self, request):
        activity_type = request.data.get("activityType") or request.data.get("activity_type") or "app_open"
        request.user.record_activity(activity_type)
        request.user.refresh_from_db(fields=["streak_count", "longest_streak", "last_visit"])
        return Response(self._payload(request.user))


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
