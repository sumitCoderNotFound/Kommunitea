"""Username rules: lowercase, 3-30 chars, [a-z0-9._], no reserved/offensive words."""
import re

from django.contrib.auth import get_user_model

USERNAME_RE = re.compile(r"^[a-z0-9._]{3,30}$")

RESERVED = {
    "admin", "support", "help", "kommunitea", "api", "auth", "login", "signup",
    "settings", "profile", "jobs", "study-match", "studymatch", "career-tools",
    "careertools", "about", "terms", "privacy", "contact", "me", "user", "users",
    "feed", "tribe", "plan", "inbox", "notifications", "explore", "search",
}

# Light offensive-word guard (substring match). Extend as needed.
_OFFENSIVE = {"fuck", "shit", "bitch", "cunt", "nigger", "faggot", "rape"}


def normalize_username(value: str) -> str:
    return (value or "").strip().lower()


def username_error(value: str) -> str | None:
    """Return an error message if invalid, else None. Does NOT check availability."""
    v = normalize_username(value)
    if not v:
        return "Username is required."
    if len(v) < 3:
        return "Username must be at least 3 characters."
    if len(v) > 30:
        return "Username must be 30 characters or fewer."
    if not USERNAME_RE.match(v):
        return "Use only lowercase letters, numbers, dots and underscores — no spaces."
    if v in RESERVED:
        return "That username is reserved. Please choose another."
    if any(bad in v for bad in _OFFENSIVE):
        return "That username isn't allowed. Please choose another."
    return None


def is_available(value: str, *, exclude_user_id=None) -> bool:
    User = get_user_model()
    v = normalize_username(value)
    qs = User.objects.filter(username=v)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    return not qs.exists()


def suggest_from_email_or_name(seed: str) -> str:
    """Build a safe candidate username from an email local-part or name."""
    base = normalize_username(re.sub(r"[^a-z0-9._]", "", (seed or "").split("@")[0].replace(" ", "")))
    base = base[:24] or "user"
    if len(base) < 3:
        base = (base + "user")[:24]
    candidate = base
    n = 0
    while not is_available(candidate) or username_error(candidate):
        n += 1
        candidate = f"{base}{n}"[:30]
        if n > 9999:
            break
    return candidate
