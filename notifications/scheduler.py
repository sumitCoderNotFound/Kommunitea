"""In-process reminder scheduler (no external cron service needed).

A BackgroundScheduler runs inside the web process and fires due reminders
every few minutes. The scan is transaction-safe so it can't double-fire
even if more than one worker is running.
"""
import logging
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
_started = False


def run_due_reminders(limit=500):
    """Fire all reminders whose due_at has passed. Returns the count fired."""
    from .models import Reminder
    fired = 0
    with transaction.atomic():
        due = (Reminder.objects
               .select_for_update(skip_locked=True)
               .filter(fired=False, due_at__lte=timezone.now())
               .order_by("due_at")[:limit])
        for r in list(due):
            try:
                r.fire()
                fired += 1
            except Exception:
                logger.exception("Failed to fire reminder %s", r.id)
    return fired


def start_scheduler():
    """Start the background scheduler exactly once."""
    global _started
    if _started:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        logger.warning("APScheduler not installed; reminders will only fire via the cron endpoint.")
        return
    scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
    # every 15 minutes; reminders are day/hour-granularity so this is plenty
    scheduler.add_job(run_due_reminders, "interval", minutes=15, id="run_due_reminders",
                      replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    _started = True
    logger.info("Reminder scheduler started (every 15 min).")
