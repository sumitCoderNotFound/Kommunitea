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
