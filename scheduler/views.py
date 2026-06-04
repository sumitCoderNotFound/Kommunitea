from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Task, WeeklyGoal, Opportunity
from .serializers import TaskSerializer, WeeklyGoalSerializer, OpportunitySerializer


@extend_schema(tags=["Scheduler"])
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["category", "priority", "completed"]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=["Scheduler"])
class WeeklyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = WeeklyGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeeklyGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=["Scheduler"])
class OpportunityListView(APIView):
    """Upcoming opportunities + community events (global rows + the user's own)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Opportunity.objects.filter(Q(user=request.user) | Q(user__isnull=True))
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return Response(OpportunitySerializer(qs, many=True).data)

    def post(self, request):
        """Add an opportunity/event into the user's scheduler as a Task."""
        opp_id = request.data.get("opportunity_id")
        try:
            opp = Opportunity.objects.get(
                Q(pk=opp_id) & (Q(user=request.user) | Q(user__isnull=True)))
        except Opportunity.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        cat = Task.Category.COMMUNITY_EVENT if opp.kind == Opportunity.Kind.EVENT else Task.Category.JOB_DEADLINE
        due = timezone.make_aware(timezone.datetime.combine(opp.deadline, timezone.datetime.min.time())) if opp.deadline else None
        task = Task.objects.create(
            user=request.user, title=opp.title, category=cat,
            due_at=due, source=Task.Source.EVENT if opp.kind == "event" else Task.Source.JOB,
            source_ref=str(opp.id),
            notes=(f"{opp.org} · {opp.location}").strip(" ·"),
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Scheduler"])
class SchedulerOverviewView(APIView):
    """Personalised header stats + AI Insights (Today's Focus) + consistency heatmap."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        u = request.user
        now = timezone.now()
        today = now.date()
        tasks = Task.objects.filter(user=u)
        incomplete = tasks.filter(completed=False)

        # header stats
        tasks_remaining = incomplete.count()
        interviews_today = incomplete.filter(
            category=Task.Category.INTERVIEW, due_at__date=today).count()
        week_end = today + timedelta(days=7)
        opps_expiring = Opportunity.objects.filter(
            Q(user=u) | Q(user__isnull=True),
            deadline__gte=today, deadline__lte=week_end).count()

        # AI insights / today's focus (rule-based)
        focus = []
        overdue = incomplete.filter(due_at__lt=now)
        nearest_deadline = incomplete.filter(
            category=Task.Category.JOB_DEADLINE, due_at__gte=now).order_by("due_at").first()
        if nearest_deadline and nearest_deadline.due_at:
            hrs = int((nearest_deadline.due_at - now).total_seconds() // 3600)
            when = f"in {hrs} hours" if hrs < 48 else nearest_deadline.due_at.strftime("on %d %b")
            focus.append({"icon": "deadline", "text": f"{nearest_deadline.title} {when}"})
        todays_interview = incomplete.filter(
            category=Task.Category.INTERVIEW, due_at__date=today).order_by("due_at").first()
        if todays_interview:
            t = todays_interview.due_at.strftime("%-I %p") if todays_interview.due_at else "today"
            focus.append({"icon": "interview", "text": f"{todays_interview.title} at {t}"})
        if overdue.exists():
            focus.append({"icon": "overdue", "text": f"{overdue.first().title} is overdue"})
        focus.append({"icon": "recommend", "text": "Apply to 3 matching jobs today"})

        # consistency heatmap: completed tasks per day, last 120 days
        since = today - timedelta(days=119)
        completed = tasks.filter(completed=True, completed_at__date__gte=since)
        counts = {}
        for t in completed:
            d = t.completed_at.date().isoformat()
            counts[d] = counts.get(d, 0) + 1
        consistency = [{"date": (since + timedelta(days=i)).isoformat(),
                        "count": counts.get((since + timedelta(days=i)).isoformat(), 0)}
                       for i in range(120)]
        tasks_this_month = tasks.filter(
            completed=True, completed_at__year=today.year, completed_at__month=today.month).count()

        return Response({
            "greeting_stats": {
                "tasks_remaining": tasks_remaining,
                "interviews_today": interviews_today,
                "opportunities_expiring": opps_expiring,
            },
            "today_focus": focus,
            "consistency": consistency,
            "streak": getattr(u, "streak_count", 0),
            "longest_streak": getattr(u, "longest_streak", 0),
            "tasks_this_month": tasks_this_month,
        })
