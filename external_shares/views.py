from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from community.models import Community, CommunityResource
from jobs.models import Job  # noqa: F401 (kept for future linking)
from posts.models import Post
from scheduler.models import JobApplication, Task

from .linkpreview import build_preview
from .models import ExternalShare
from accounts.throttles import SharePreviewThrottle
from .serializers import ExternalShareSerializer


class ExternalShareViewSet(viewsets.ModelViewSet):
    """Bring external content in. Preview never scrapes IG/LI/WhatsApp."""
    serializer_class = ExternalShareSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return ExternalShare.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="preview",
            throttle_classes=[SharePreviewThrottle])
    def preview(self, request):
        url = (request.data.get("sourceUrl") or request.data.get("url") or "").strip()
        text = (request.data.get("sourceText") or request.data.get("text") or "").strip()
        image = (request.data.get("sourceImage") or request.data.get("image") or "").strip()
        if not url and not text and not image:
            return Response({"detail": "Paste a link or some text first."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_preview(url, text, image))

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        user = request.user
        community_id = v.pop("communityId", "")

        share = ExternalShare(
            user=user,
            source_platform=v.get("source_platform", "website"),
            source_url=v.get("source_url", ""),
            source_text=v.get("source_text", ""),
            source_image=v.get("source_image", ""),
            source_video=v.get("source_video", ""),
            title=v.get("title", ""),
            description=v.get("description", ""),
            thumbnail=v.get("thumbnail", ""),
            destination_type=v.get("destination_type", ""),
            status=ExternalShare.Status.IMPORTED,
        )

        dest = share.destination_type
        attribution = f"Imported from {share.get_source_platform_display()}"

        try:
            if dest == ExternalShare.Destination.POST:
                body = "\n\n".join(p for p in [share.title, share.description, share.source_url, attribution] if p)
                obj = Post.objects.create(author=user, body=body[:5000])
                share.destination_id = str(obj.id)

            elif dest == ExternalShare.Destination.COMMUNITY_RESOURCE:
                if not community_id:
                    return Response({"detail": "communityId is required for a community resource."},
                                    status=status.HTTP_400_BAD_REQUEST)
                community = Community.objects.filter(id=community_id, members=user).first()
                if not community:
                    return Response({"detail": "You must be a member of that community."},
                                    status=status.HTTP_403_FORBIDDEN)
                obj = CommunityResource.objects.create(
                    community=community, title=(share.title or "Shared link")[:160],
                    url=share.source_url, description=share.description,
                )
                share.destination_id = str(obj.id)

            elif dest == ExternalShare.Destination.PLAN:
                notes = "\n".join(p for p in [share.description, share.source_url, attribution] if p)
                obj = Task.objects.create(user=user, title=(share.title or "Imported item")[:200], notes=notes)
                share.destination_id = str(obj.id)

            elif dest == ExternalShare.Destination.JOB_APPLICATION:
                obj = JobApplication.objects.create(
                    user=user, company=(share.title or "Imported role")[:160],
                    role_title=(share.title or "")[:160], job_link=share.source_url,
                    source=share.get_source_platform_display(), status="saved",
                    notes=share.description,
                )
                share.destination_id = str(obj.id)
            # story / message / saved → recorded only; client handles media/recipient
        except Exception as exc:  # pragma: no cover - defensive
            return Response({"detail": f"Could not create destination item: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)

        share.save()
        return Response(self.get_serializer(share).data, status=status.HTTP_201_CREATED)
