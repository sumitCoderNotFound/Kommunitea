from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from notifications.models import Notification

User = get_user_model()


@extend_schema(tags=["Messaging"])
class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = self.request.user.conversations.prefetch_related("participants", "messages")
        only_requests = self.request.query_params.get("requests") == "true"
        if only_requests:
            # requests I received (someone else started, still pending)
            return qs.filter(is_request=True).exclude(initiator=self.request.user)
        # normal inbox: accepted convos, or ones I started
        from django.db.models import Q
        return qs.filter(Q(is_request=False) | Q(initiator=self.request.user))

    def create(self, request):
        """Start (or fetch) a conversation with {userId}."""
        other_id = request.data.get("userId") or request.data.get("user_id")
        other = User.objects.filter(pk=other_id).first()
        if not other:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        convo = Conversation.between(request.user, other)
        # New conversation from someone the recipient doesn't follow -> message request
        if convo.initiator is None:
            convo.initiator = request.user
            # if the other person already follows me, it's a normal chat; else a request
            follows_me = other.following.filter(pk=request.user.pk).exists()
            convo.is_request = not follows_me
            convo.save()
        return Response(self.get_serializer(convo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        # Look across all the user's conversations (not the filtered inbox),
        # so a pending request can be found and accepted.
        convo = request.user.conversations.filter(pk=pk).first()
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        convo.is_request = False
        convo.save()
        return Response({"detail": "Accepted."})

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        convo = self.get_object()
        if request.method == "POST":
            body = request.data.get("body", "").strip()
            if not body:
                return Response({"detail": "Empty message."}, status=status.HTTP_400_BAD_REQUEST)
            msg = Message.objects.create(conversation=convo, sender=request.user, body=body)
            convo.save()  # bump updated_at
            other = convo.participants.exclude(pk=request.user.pk).first()
            if other:
                Notification.push(other, request.user, Notification.Verb.MESSAGE, text=body[:60])
            return Response(MessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)
        # GET: mark incoming as read, return all
        convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        data = MessageSerializer(convo.messages.all(), many=True, context={"request": request}).data
        return Response(data)
