from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import CVAnalysis, ReferralRequest, InterviewPrep
from .serializers import CVAnalysisSerializer, ReferralRequestSerializer, InterviewPrepSerializer
from .scoring import extract_text, analyze

DEFAULT_CHECKLIST = [
    "Research company", "Review job description", "Prepare STAR answers",
    "Prepare project examples", "Prepare right-to-work / visa answer",
    "Prepare questions for interviewer", "Complete mock interview",
    "Confirm interview time / link",
]
COMMON_QUESTIONS = [
    "Tell me about yourself.",
    "Why do you want this role?",
    "Describe a challenge you overcame (STAR).",
    "What are your strengths and weaknesses?",
    "Why this company?",
    "Where do you see yourself in 3 years?",
    "Do you have the right to work in the UK / need sponsorship?",
]


@extend_schema(tags=["Career"])
class CVAnalysisViewSet(viewsets.ModelViewSet):
    """CV ATS Review reports. POST /cv/analyze/ runs rule-based scoring on an uploaded file."""
    serializer_class = CVAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return CVAnalysis.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="analyze")
    def analyze_cv(self, request):
        f = request.FILES.get("file")
        text = request.data.get("text", "")  # allow pasted text too
        job_description = request.data.get("jobDescription", "") or request.data.get("job_description", "")
        file_name = ""
        if f:
            file_name = f.name
            text = extract_text(f, f.name)
        if not text or len(text.strip()) < 30:
            return Response({"detail": "Could not read enough text from the CV. Upload a PDF/DOCX or paste your CV text."},
                            status=status.HTTP_400_BAD_REQUEST)
        result = analyze(text, job_description)
        report = CVAnalysis.objects.create(
            user=request.user, file_name=file_name, extracted_text=text[:20000], **result)
        # privacy: we do not persist the uploaded file (auto-delete after analysis)
        from notifications.models import Notification
        Notification.remind(request.user, f"Your CV review is ready - ATS score {report.ats_score}/100",
                            target_type="cv", target_id=str(report.id))
        return Response(CVAnalysisSerializer(report).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Career"])
class ReferralRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        return ReferralRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        ref = serializer.save(user=self.request.user)
        self._sync_reminder(ref)

    def perform_update(self, serializer):
        ref = serializer.save()
        self._sync_reminder(ref)

    def _sync_reminder(self, ref):
        from datetime import datetime, time
        from django.utils import timezone
        from notifications.models import Reminder
        Reminder.objects.filter(kind="referral_follow_up", referral_id=str(ref.id), fired=False).delete()
        if ref.follow_up_date and ref.status in ("requested", "follow_up"):
            due = timezone.make_aware(datetime.combine(ref.follow_up_date, time(9, 0)))
            Reminder.objects.create(user=ref.user, kind="referral_follow_up",
                                    text=f"Follow up on your referral to {ref.company}",
                                    due_at=due, target_type="referral", referral_id=str(ref.id))


@extend_schema(tags=["Career"])
class InterviewPrepViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewPrepSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InterviewPrep.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # seed default checklist + common questions if none provided
        checklist = serializer.validated_data.get("checklist") or [{"item": i, "done": False} for i in DEFAULT_CHECKLIST]
        questions = serializer.validated_data.get("questions") or COMMON_QUESTIONS
        prep = serializer.save(user=self.request.user, checklist=checklist, questions=questions)
        self._sync_reminder(prep)

    def perform_update(self, serializer):
        prep = serializer.save()
        self._sync_reminder(prep)

    def _sync_reminder(self, prep):
        from datetime import timedelta
        from notifications.models import Reminder
        Reminder.objects.filter(kind="interview", target_id=str(prep.id), fired=False).delete()
        if prep.interview_date:
            due = prep.interview_date - timedelta(days=1)
            Reminder.objects.create(user=prep.user, kind="interview",
                                    text=f"Interview tomorrow: {prep.role_title or 'role'} at {prep.company}",
                                    due_at=due, target_type="interview_prep", target_id=str(prep.id))

    @action(detail=True, methods=["post"], url_path="complete-checklist-item")
    def complete_item(self, request, pk=None):
        prep = self.get_object()
        idx = request.data.get("index")
        done = request.data.get("done", True)
        try:
            prep.checklist[int(idx)]["done"] = bool(done)
        except (IndexError, ValueError, TypeError, KeyError):
            return Response({"detail": "Invalid checklist index."}, status=status.HTTP_400_BAD_REQUEST)
        completed = sum(1 for c in prep.checklist if c.get("done"))
        prep.confidence_score = round((completed / len(prep.checklist)) * 100) if prep.checklist else 0
        prep.save(update_fields=["checklist", "confidence_score", "updated_at"])
        return Response(InterviewPrepSerializer(prep).data)
