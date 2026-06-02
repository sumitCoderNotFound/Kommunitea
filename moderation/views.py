from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from .models import Report, Block
from .serializers import ReportSerializer

User = get_user_model()


@extend_schema(tags=["Moderation"])
class ReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Any logged-in user can file a report on a post, comment, or user."""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


@extend_schema(tags=["Moderation"])
class BlockViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        ids = list(request.user.blocking.values_list("blocked_id", flat=True))
        return Response({"blocked": ids})

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        if str(request.user.pk) == str(pk):
            return Response({"detail": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)
        target = User.objects.filter(pk=pk).first()
        if not target:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        Block.objects.get_or_create(blocker=request.user, blocked=target)
        # blocking also unfollows both ways
        request.user.following.remove(target)
        target.following.remove(request.user)
        return Response({"detail": "Blocked."})

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        Block.objects.filter(blocker=request.user, blocked_id=pk).delete()
        return Response({"detail": "Unblocked."})
