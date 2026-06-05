from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from notifications.models import Notification

User = get_user_model()


def _touch_presence(user):
    """Update the user's last_seen for presence ('online') without extra queries."""
    User.objects.filter(pk=user.pk).update(last_seen=timezone.now())


@extend_schema(tags=["Messaging"])
class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        _touch_presence(self.request.user)
        qs = self.request.user.conversations.prefetch_related("participants", "messages")
        params = self.request.query_params
        if params.get("requests") == "true":
            return qs.filter(is_request=True).exclude(initiator=self.request.user)
        kind = params.get("kind")
        if kind in (Conversation.Kind.GROUP, Conversation.Kind.COMMUNITY, Conversation.Kind.BROADCAST):
            return qs.filter(kind=kind)
        if kind == "primary":
            return qs.filter(Q(is_request=False) | Q(initiator=self.request.user)).filter(kind=Conversation.Kind.DIRECT)
        # default inbox: accepted convos or ones I started (all kinds)
        return qs.filter(Q(is_request=False) | Q(initiator=self.request.user))

    def create(self, request):
        """Start (or fetch) a 1-on-1 conversation with {userId}."""
        other_id = request.data.get("userId") or request.data.get("user_id")
        other = User.objects.filter(pk=other_id).first()
        if not other:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        convo = Conversation.between(request.user, other)
        if convo.initiator is None:
            convo.initiator = request.user
            follows_me = other.following.filter(pk=request.user.pk).exists()
            convo.is_request = not follows_me
            convo.save()
        return Response(self.get_serializer(convo).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="group")
    def create_group(self, request):
        """Create a group / community chat / broadcast.
        Body: { title, participantIds: [...], kind: 'group'|'community'|'broadcast' }"""
        title = (request.data.get("title") or "").strip()
        ids = request.data.get("participantIds") or request.data.get("participant_ids") or []
        kind = request.data.get("kind") or Conversation.Kind.GROUP
        if kind not in (Conversation.Kind.GROUP, Conversation.Kind.COMMUNITY, Conversation.Kind.BROADCAST):
            kind = Conversation.Kind.GROUP
        if not title:
            return Response({"detail": "A title is required."}, status=status.HTTP_400_BAD_REQUEST)
        members = list(User.objects.filter(pk__in=ids).exclude(pk=request.user.pk))
        convo = Conversation.objects.create(kind=kind, title=title, owner=request.user, is_request=False)
        convo.participants.add(request.user, *members)
        # notify added members
        for m in members:
            Notification.push(m, request.user, Notification.Verb.MESSAGE, text=f"added you to {title}")
        return Response(self.get_serializer(convo).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="ai")
    def ai_assistant(self, request):
        """Get or create the user's AI Career Assistant conversation."""
        convo = request.user.conversations.filter(kind=Conversation.Kind.AI).first()
        if not convo:
            convo = Conversation.objects.create(kind=Conversation.Kind.AI, title="AI Career Assistant",
                                                owner=request.user, is_request=False)
            convo.participants.add(request.user)
            Message.objects.create(conversation=convo, sender=None, is_ai=True,
                                   body="Hi! I'm your AI Career Assistant. Ask me about CVs, interviews, job search, visas or networking in the UK.")
        return Response(self.get_serializer(convo).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        convo = request.user.conversations.filter(pk=pk).first()
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        convo.is_request = False
        convo.save()
        return Response({"detail": "Accepted."})

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        convo = self.get_object()
        _touch_presence(request.user)
        if request.method == "POST":
            body = request.data.get("body", "").strip()
            if not body:
                return Response({"detail": "Empty message."}, status=status.HTTP_400_BAD_REQUEST)
            msg = Message.objects.create(conversation=convo, sender=request.user, body=body)
            convo.save()  # bump updated_at

            if convo.kind == Conversation.Kind.AI:
                # generate an assistant reply inline
                from ai.services import career_assistant_reply
                history = [{"body": m.body, "is_ai": m.is_ai} for m in convo.messages.all()]
                profile = {
                    "full_name": request.user.full_name, "course": request.user.course,
                    "university": request.user.university, "skills": request.user.skills,
                }
                reply_text = career_assistant_reply(body, history=history, profile=profile)
                Message.objects.create(conversation=convo, sender=None, is_ai=True, body=reply_text)
                convo.save()
            else:
                # notify other participants (skip self)
                for other in convo.participants.exclude(pk=request.user.pk):
                    Notification.push(other, request.user, Notification.Verb.MESSAGE, text=body[:60])
            return Response(MessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)

        # GET: mark incoming as read, return all
        convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        data = MessageSerializer(convo.messages.all(), many=True, context={"request": request}).data
        return Response(data)
