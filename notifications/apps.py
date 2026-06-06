import os
import sys
from django.apps import AppConfig


# Management commands that should NOT start the background scheduler.
_SKIP_COMMANDS = {"migrate", "makemigrations", "collectstatic", "shell", "test",
                  "createsuperuser", "loaddata", "dumpdata", "check", "showmigrations"}


class NotificationsConfig(AppConfig):
    name = "notifications"

    def ready(self):
        # Don't start during one-off management commands (e.g. release-phase migrate).
        argv = sys.argv
        if len(argv) > 1 and argv[1] in _SKIP_COMMANDS:
            return
        # Under runserver's autoreloader, only start in the worker process.
        if "runserver" in argv and os.environ.get("RUN_MAIN") != "true":
            return
        # Allow opting out explicitly.
        if os.environ.get("ENABLE_SCHEDULER", "1") == "0":
            return
        try:
            from .scheduler import start_scheduler
            start_scheduler()
        except Exception:
            pass
