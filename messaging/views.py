from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import Conversation, Message, MessageReaction
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
            Notification.push(m, request.user, Notification.Verb.MESSAGE, text=f"added you to {title}", conversation_id=convo.id)
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

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Decline a message request: remove the receiver from the conversation."""
        convo = request.user.conversations.filter(pk=pk).first()
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        convo.participants.remove(request.user)
        # if nobody meaningful is left, drop the conversation entirely
        if convo.participants.count() <= 1:
            convo.delete()
        return Response({"detail": "Declined."})

    @action(detail=False, methods=["get"])
    def counts(self, request):
        """Badge counts: pending message requests + total unread across the inbox."""
        user = request.user
        convos = user.conversations.all()
        # unread request conversations (someone messaged me, not yet accepted)
        request_convos = convos.filter(is_request=True).exclude(initiator=user)
        request_count = sum(
            1 for c in request_convos
            if c.messages.filter(is_read=False).exclude(sender=user).exists()
        )
        # total unread messages across accepted inbox + requests
        unread_total = (
            Message.objects.filter(conversation__in=convos, is_read=False)
            .exclude(sender=user).count()
        )
        return Response({"request_count": request_count, "unread_total": unread_total})

    @action(detail=True, methods=["get", "post"],
            parser_classes=[MultiPartParser, FormParser, JSONParser])
    def messages(self, request, pk=None):
        convo = self.get_object()
        _touch_presence(request.user)
        if request.method == "POST":
            kind = request.data.get("kind", "text")
            body = (request.data.get("body") or "").strip()
            gif_url = (request.data.get("gifUrl") or request.data.get("gif_url") or "").strip()
            view_once = str(request.data.get("viewOnce") or request.data.get("view_once") or "").lower() in ("1", "true", "yes")
            image = request.FILES.get("image")
            doc = request.FILES.get("file")
            lat = request.data.get("lat")
            lng = request.data.get("lng")
            shared_id = (request.data.get("sharedId") or request.data.get("shared_id") or "")
            shared_payload = request.data.get("sharedPayload") or request.data.get("shared_payload")
            shared_kinds = ("shared_post", "shared_profile", "shared_job", "shared_community")

            if kind not in dict(Message.Kind.choices):
                kind = "text"
            if view_once and image:
                kind = Message.Kind.VIEW_ONCE
            if gif_url and kind == "text":
                kind = Message.Kind.GIF
            if doc and kind == "text":
                kind = Message.Kind.DOCUMENT
            if (lat not in (None, "")) and (lng not in (None, "")) and kind == "text":
                kind = Message.Kind.LOCATION

            has_location = (lat not in (None, "")) and (lng not in (None, ""))
            is_shared = kind in shared_kinds
            if not body and not image and not gif_url and not doc and not has_location and not is_shared:
                return Response({"detail": "Empty message."}, status=status.HTTP_400_BAD_REQUEST)

            msg = Message.objects.create(
                conversation=convo, sender=request.user, body=body, kind=kind,
                image=image if image else None, file=doc if doc else None,
                file_name=(getattr(doc, "name", "") or "")[:200] if doc else "",
                gif_url=gif_url,
                lat=float(lat) if has_location else None, lng=float(lng) if has_location else None,
                shared_id=str(shared_id) if is_shared else "",
                shared_payload=shared_payload if is_shared else None,
            )
            convo.save()  # bump updated_at

            if convo.kind == Conversation.Kind.AI:
                from ai.services import career_assistant_reply
                history = [{"body": m.body, "is_ai": m.is_ai} for m in convo.messages.all()]
                profile = {"full_name": request.user.full_name, "course": request.user.course,
                           "university": request.user.university, "skills": request.user.skills}
                reply_text = career_assistant_reply(body, history=history, profile=profile)
                Message.objects.create(conversation=convo, sender=None, is_ai=True, body=reply_text)
                convo.save()
            else:
                preview = body[:60] if body else {
                    "gif": "GIF", "image": "Photo", "view_once": "Photo", "doodle": "Doodle",
                    "document": "Document", "location": "Location",
                }.get(kind, "Message")
                for other in convo.participants.exclude(pk=request.user.pk):
                    Notification.push(other, request.user, Notification.Verb.MESSAGE, text=preview, conversation_id=convo.id)
            return Response(MessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)

        # GET: mark incoming as read, return all
        convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        data = MessageSerializer(convo.messages.prefetch_related("reactions").all(), many=True, context={"request": request}).data
        return Response(data)

    @action(detail=True, methods=["post"], url_path=r"messages/(?P<message_id>[^/.]+)/open")
    def open_view_once(self, request, pk=None, message_id=None):
        """Recipient opens a view-once photo. Returns the image URL once, then expires it."""
        convo = self.get_object()
        msg = convo.messages.filter(pk=message_id, kind=Message.Kind.VIEW_ONCE).first()
        if not msg:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if msg.sender_id == request.user.pk:
            # sender can't consume their own; just report state
            return Response({"viewed": msg.viewed_at is not None, "imageUrl": ""})
        if msg.viewed_at is not None:
            return Response({"viewed": True, "imageUrl": "", "detail": "Already viewed."})
        url = request.build_absolute_uri(msg.image.url) if msg.image else ""
        msg.viewed_at = timezone.now()
        msg.save(update_fields=["viewed_at"])
        if msg.sender_id:
            Notification.push(msg.sender, request.user, Notification.Verb.VIEW_ONCE_OPENED, text="opened your photo", conversation_id=convo.id)
        return Response({"viewed": True, "imageUrl": url})

    @action(detail=True, methods=["post"], url_path=r"messages/(?P<message_id>[^/.]+)/react")
    def react(self, request, pk=None, message_id=None):
        """Toggle/replace the current user's emoji reaction on a message. Empty emoji removes it."""
        convo = self.get_object()
        msg = convo.messages.filter(pk=message_id).first()
        if not msg:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        emoji = (request.data.get("emoji") or "").strip()
        existing = MessageReaction.objects.filter(message=msg, user=request.user).first()
        if not emoji or (existing and existing.emoji == emoji):
            if existing:
                existing.delete()
        else:
            MessageReaction.objects.update_or_create(message=msg, user=request.user, defaults={"emoji": emoji})
            if msg.sender_id and msg.sender_id != request.user.pk:
                Notification.push(msg.sender, request.user, Notification.Verb.MESSAGE_REACTION, text=emoji, conversation_id=convo.id)
        return Response(MessageSerializer(msg, context={"request": request}).data)
