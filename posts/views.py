from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from .models import Post, Comment
from .serializers import PostSerializer, CommentSerializer
from notifications.models import Notification


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


@extend_schema(tags=["Posts"])
class PostViewSet(viewsets.ModelViewSet):
    """Community feed: list/create posts, like, save, and comment."""
    serializer_class = PostSerializer
    queryset = Post.objects.select_related("author").prefetch_related("comments", "liked_by", "saved_by")
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["category", "author"]
    search_fields = ["body", "author__full_name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        # Only editing/deleting the post itself requires being the author.
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        # create, like, save, comment just require being logged in.
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if self.request.query_params.get("mine") == "true" and user.is_authenticated:
            return qs.filter(author=user)
        if user.is_authenticated:
            # Hide posts from people I blocked or who blocked me
            blocked = user.blocking.values_list("blocked_id", flat=True)
            blocked_by = user.blocked_by.values_list("blocker_id", flat=True)
            qs = qs.exclude(author_id__in=list(blocked) + list(blocked_by))
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        post = self.get_object()
        if post.liked_by.filter(pk=request.user.pk).exists():
            post.liked_by.remove(request.user)
        else:
            post.liked_by.add(request.user)
            Notification.push(post.author, request.user, Notification.Verb.LIKE, post_id=post.id)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], url_path="save")
    def save_post(self, request, pk=None):
        post = self.get_object()
        if post.saved_by.filter(pk=request.user.pk).exists():
            post.saved_by.remove(request.user)
        else:
            post.saved_by.add(request.user)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], url_path="comments")
    def comments(self, request, pk=None):
        post = self.get_object()
        body = request.data.get("body", "").strip()
        if not body:
            return Response({"detail": "Comment cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        comment = Comment.objects.create(post=post, author=request.user, body=body)
        Notification.push(post.author, request.user, Notification.Verb.COMMENT, text=body[:60], post_id=post.id)
        return Response(CommentSerializer(comment, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


from django.utils import timezone  # noqa: E402
from .models import Story  # noqa: E402
from .serializers import StorySerializer  # noqa: E402
from rest_framework.parsers import MultiPartParser as _MP, FormParser as _FP  # noqa: E402


@extend_schema(tags=["Stories"])
class StoryViewSet(viewsets.ModelViewSet):
    """Instagram-style stories. Only active (non-expired) stories are listed,
    grouped client-side by author."""
    serializer_class = StorySerializer
    parser_classes = [_MP, _FP]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return (Story.objects
                .filter(expires_at__gt=timezone.now())
                .select_related("author")
                .order_by("author", "-created_at"))

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
