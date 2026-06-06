from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=["Notifications"])
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.select_related("actor")

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": request.user.notifications.filter(is_read=False).count()})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response({"detail": "All marked read."})

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        n = request.user.notifications.filter(pk=pk).first()
        if not n:
            return Response({"detail": "Not found."}, status=404)
        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])
        return Response({"detail": "Marked read."})


from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.conf import settings as dj_settings
from .models import Reminder


class RunRemindersView(APIView):
    """Cron endpoint: fire all due reminders into notifications.
    Protected by the X-Cron-Secret header matching CRON_SECRET."""
    permission_classes = [AllowAny]

    def post(self, request):
        secret = getattr(dj_settings, "CRON_SECRET", None)
        if secret and request.headers.get("X-Cron-Secret") != secret:
            return Response({"detail": "Forbidden."}, status=403)
        from .scheduler import run_due_reminders
        return Response({"fired": run_due_reminders()})
