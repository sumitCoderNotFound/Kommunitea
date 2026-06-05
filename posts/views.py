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
from django.db.models import Q  # noqa: E402
from .models import Story  # noqa: E402
from .serializers import StorySerializer  # noqa: E402
from rest_framework.parsers import MultiPartParser as _MP, FormParser as _FP, JSONParser as _JP  # noqa: E402


@extend_schema(tags=["Stories"])
class StoryViewSet(viewsets.ModelViewSet):
    """Instagram-style stories. Only active (non-expired) stories the viewer is
    allowed to see are listed, grouped client-side by author."""
    serializer_class = StorySerializer
    parser_classes = [_MP, _FP, _JP]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        active = (Story.objects
                  .filter(expires_at__gt=timezone.now())
                  .select_related("author")
                  .order_by("author", "-created_at"))
        user = self.request.user
        if not (user and user.is_authenticated):
            # anonymous only sees public stories
            return active.filter(visibility=Story.Visibility.PUBLIC)
        # public, own stories, or follower/community stories where I follow the author
        followed_author_ids = user.following.values_list("pk", flat=True)
        return active.filter(
            Q(visibility=Story.Visibility.PUBLIC)
            | Q(author=user)
            | Q(visibility__in=[Story.Visibility.FOLLOWERS, Story.Visibility.COMMUNITY], author__in=followed_author_ids)
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        story = self.get_object()
        if not story.visible_to(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if story.liked_by.filter(pk=request.user.pk).exists():
            story.liked_by.remove(request.user)
            liked = False
        else:
            story.liked_by.add(request.user)
            liked = True
            if story.author_id != request.user.pk:
                Notification.push(story.author, request.user, Notification.Verb.STORY_LIKE)
        return Response({"liked": liked, "likes_count": story.liked_by.count()})

    @action(detail=True, methods=["post"])
    def view(self, request, pk=None):
        story = self.get_object()
        if story.visible_to(request.user) and story.author_id != request.user.pk:
            story.viewed_by.add(request.user)
        return Response({"views_count": story.viewed_by.count()})

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        """Reply to a story -> sends a DM to the story author."""
        story = self.get_object()
        if not story.visible_to(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "Empty reply."}, status=status.HTTP_400_BAD_REQUEST)
        if story.author_id == request.user.pk:
            return Response({"detail": "You cannot reply to your own story."}, status=status.HTTP_400_BAD_REQUEST)
        from messaging.models import Conversation, Message
        convo = Conversation.between(request.user, story.author)
        if convo.initiator is None:
            convo.initiator = request.user
            follows_me = story.author.following.filter(pk=request.user.pk).exists()
            convo.is_request = not follows_me
            convo.save()
        Message.objects.create(conversation=convo, sender=request.user, body=f"Replied to your story: {body}")
        convo.save()
        Notification.push(story.author, request.user, Notification.Verb.STORY_REPLY, text=body[:60])
        return Response({"detail": "Reply sent.", "conversation_id": str(convo.pk)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        """Share a story to chosen users. Private stories cannot be shared by others."""
        story = self.get_object()
        if not story.visible_to(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if story.visibility == Story.Visibility.PRIVATE and story.author_id != request.user.pk:
            return Response({"detail": "Private stories cannot be shared."}, status=status.HTTP_403_FORBIDDEN)
        target_ids = request.data.get("userIds") or request.data.get("user_ids") or []
        if isinstance(target_ids, str):
            target_ids = [target_ids]
        from messaging.models import Conversation, Message
        from accounts.models import User
        sent = 0
        for uid in target_ids:
            target = User.objects.filter(pk=uid).first()
            if not target or target.pk == request.user.pk:
                continue
            convo = Conversation.between(request.user, target)
            if convo.initiator is None:
                convo.initiator = request.user
                follows_me = target.following.filter(pk=request.user.pk).exists()
                convo.is_request = not follows_me
                convo.save()
            Message.objects.create(conversation=convo, sender=request.user,
                                   body=f"Shared a story by {story.author.full_name}")
            convo.save()
            sent += 1
        if story.author_id != request.user.pk and sent:
            Notification.push(story.author, request.user, Notification.Verb.STORY_SHARE)
        return Response({"detail": f"Shared with {sent} people.", "shared": sent})
