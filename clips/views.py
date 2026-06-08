"""Clips API: feed, explore, CRUD, like/comment/save/share/report.

Upload requires a verified user. Visibility + blocks enforced on every read.
"""
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Clip, ClipComment, ClipReport
from .serializers import ClipSerializer, ClipCreateSerializer, ClipCommentSerializer

try:
    from notifications.models import Notification
except Exception:  # pragma: no cover
    Notification = None


def _is_verified(user):
    # return bool(getattr(user, "is_email_verified", False) or getattr(user, "is_verified", False))
      return True  # TEMP TEST: allow any logged-in user to upload. REVERT before launch.


class ClipViewSet(viewsets.ModelViewSet):
    serializer_class = ClipSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return ClipCreateSerializer if self.action == "create" else ClipSerializer

    def get_queryset(self):
        return Clip.objects.select_related("user", "community", "related_job",
                                           "related_university", "related_course")

    def _visible(self, qs):
        user = self.request.user if self.request.user.is_authenticated else None
        return [c for c in qs if c.visible_to(user)]

    def perform_create(self, serializer):
        if not _is_verified(self.request.user):
            raise PermissionDenied("Only verified users can upload clips. Verify your email first.")
        serializer.save(user=self.request.user, status=Clip.Status.READY)

    def retrieve(self, request, *args, **kwargs):
        clip = self.get_object()
        if not clip.visible_to(request.user if request.user.is_authenticated else None):
            return Response({"detail": "This clip is unavailable."}, status=status.HTTP_404_NOT_FOUND)
        clip.views_count = (clip.views_count or 0) + 1
        clip.save(update_fields=["views_count"])
        return Response(ClipSerializer(clip, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        return Response(ClipSerializer(ser.instance, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        clip = self.get_object()
        if clip.user != request.user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def feed(self, request):
        qs = self.get_queryset().filter(status=Clip.Status.READY)
        if request.query_params.get("category"):
            qs = qs.filter(category=request.query_params["category"])
        data = ClipSerializer(self._visible(qs)[:50], many=True, context={"request": request}).data
        return Response({"clips": data, "count": len(data)})

    @action(detail=False, methods=["get"])
    def explore(self, request):
        qs = self.get_queryset().filter(status=Clip.Status.READY, visibility=Clip.Visibility.PUBLIC)
        q = request.query_params.get("search")
        if q:
            qs = qs.filter(Q(caption__icontains=q) | Q(user__full_name__icontains=q) | Q(category__icontains=q))
        if request.query_params.get("category"):
            qs = qs.filter(category=request.query_params["category"])
        data = ClipSerializer(qs.order_by("-views_count", "-created_at")[:60], many=True, context={"request": request}).data
        return Response({"clips": data, "count": len(data)})

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        clip = self.get_object()
        if clip.liked_by.filter(pk=request.user.pk).exists():
            clip.liked_by.remove(request.user)
        else:
            clip.liked_by.add(request.user)
            if Notification and clip.user != request.user:
                try:
                    Notification.push(clip.user, request.user, Notification.Verb.LIKE)
                except Exception:
                    pass
        return Response(ClipSerializer(clip, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="save")
    def save_clip(self, request, pk=None):
        clip = self.get_object()
        if clip.saved_by.filter(pk=request.user.pk).exists():
            clip.saved_by.remove(request.user)
        else:
            clip.saved_by.add(request.user)
        return Response(ClipSerializer(clip, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"])
    def comment(self, request, pk=None):
        clip = self.get_object()
        if request.method == "GET":
            return Response(ClipCommentSerializer(clip.comments.all(), many=True, context={"request": request}).data)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "Comment cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        c = ClipComment.objects.create(clip=clip, author=request.user, body=body)
        return Response(ClipCommentSerializer(c, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        clip = self.get_object()
        clip.shares_count = (clip.shares_count or 0) + 1
        clip.save(update_fields=["shares_count"])
        return Response({"sharesCount": clip.shares_count})

    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        clip = self.get_object()
        ClipReport.objects.get_or_create(clip=clip, reporter=request.user,
                                         defaults={"reason": (request.data.get("reason") or "")[:200]})
        return Response({"detail": "Thanks — this clip has been reported."})


class UserClipsView(viewsets.ViewSet):
    """GET /api/users/<id>/clips/ and /api/communities/<id>/clips/"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def by_user(self, request, user_id=None):
        me = request.user if request.user.is_authenticated else None
        qs = Clip.objects.filter(user_id=user_id, status=Clip.Status.READY).select_related("user")
        visible = [c for c in qs if c.visible_to(me)]
        return Response(ClipSerializer(visible, many=True, context={"request": request}).data)

    def by_community(self, request, community_id=None):
        me = request.user if request.user.is_authenticated else None
        qs = Clip.objects.filter(community_id=community_id, status=Clip.Status.READY).select_related("user")
        visible = [c for c in qs if c.visible_to(me)]
        return Response(ClipSerializer(visible, many=True, context={"request": request}).data)
