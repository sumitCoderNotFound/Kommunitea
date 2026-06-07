"""Link/text classification + SAFE metadata preview.

Rules enforced here:
  * Instagram / LinkedIn / WhatsApp are NEVER fetched server-side (no scraping).
    We classify by URL pattern and use only the text the user pasted.
  * Generic websites: we fetch Open Graph / <title> metadata with an SSRF guard
    (no private/loopback/link-local IPs), short timeout and a size cap.
"""
import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests

JOB_KEYWORDS = ("job", "hiring", "vacancy", "role", "apply", "graduate", "internship", "sponsor")
HOUSING_KEYWORDS = ("rent", "flat", "room", "accommodation", "housing", "tenant", "studio", "lease")

PLATFORM = {
    "instagram": "instagram",
    "linkedin": "linkedin",
    "whatsapp": "whatsapp",
    "website": "website",
    "text": "text",
}


def detect_platform(url: str, text: str) -> str:
    if url:
        host = (urlparse(url).hostname or "").lower()
        if "instagram.com" in host or host == "instagr.am":
            return "instagram"
        if "linkedin.com" in host or host == "lnkd.in":
            return "linkedin"
        if "whatsapp.com" in host or host == "wa.me":
            return "whatsapp"
        return "website"
    return "text"


def suggest_destinations(platform: str, url: str, text: str) -> list[str]:
    blob = f"{url} {text}".lower()
    if platform == "linkedin":
        if "/jobs/" in url.lower() or any(k in blob for k in JOB_KEYWORDS):
            return ["job_application", "plan", "post"]
        return ["post", "message", "saved"]
    if platform == "instagram":
        return ["post", "story", "message"]
    if platform in ("whatsapp", "text"):
        if any(k in blob for k in JOB_KEYWORDS):
            return ["plan", "job_application", "community_resource"]
        if any(k in blob for k in HOUSING_KEYWORDS):
            return ["community_resource", "plan", "post"]
        return ["post", "community_resource", "message"]
    # generic website
    if any(k in blob for k in JOB_KEYWORDS):
        return ["job_application", "plan", "post", "community_resource"]
    if any(k in blob for k in HOUSING_KEYWORDS):
        return ["community_resource", "plan", "post"]
    return ["post", "community_resource", "saved", "plan"]


def _is_public_host(host: str) -> bool:
    """Resolve host and ensure every address is a routable public IP (SSRF guard)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return False
    return True


_OG = lambda prop, html: (re.search(  # noqa: E731
    rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I) or [None, ""])[1]


def fetch_website_metadata(url: str) -> dict:
    """Fetch OG/<title> metadata for a generic website. Returns {} on any failure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {}
    if not _is_public_host(parsed.hostname):
        return {}
    try:
        resp = requests.get(
            url, timeout=5, allow_redirects=True, stream=True,
            headers={"User-Agent": "KommuniteaBot/1.0 (+link-preview)"},
        )
        # Re-validate the final host after redirects.
        final_host = urlparse(resp.url).hostname or ""
        if not _is_public_host(final_host):
            return {}
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            return {}
        html = resp.raw.read(512_000, decode_content=True).decode("utf-8", "ignore")
    except Exception:
        return {}

    title = _OG("og:title", html) or (
        (re.search(r"<title[^>]*>([^<]+)</title>", html, re.I) or [None, ""])[1]).strip()
    desc = _OG("og:description", html) or _OG("description", html)
    image = _OG("og:image", html)
    return {"title": title[:300], "description": desc[:1000], "thumbnail": image[:1000]}


def build_preview(url: str, text: str, image: str = "") -> dict:
    platform = detect_platform(url, text)
    data = {
        "sourcePlatform": platform,
        "sourceUrl": url or "",
        "sourceText": text or "",
        "sourceImage": image or "",
        "title": "",
        "description": text[:1000] if text else "",
        "thumbnail": image or "",
        "suggestedDestinations": suggest_destinations(platform, url, text),
        "attribution": f"Imported from {PLATFORM.get(platform, 'the web').title()}",
    }
    # Only fetch metadata for generic websites (never scrape IG/LI/WhatsApp).
    if platform == "website":
        meta = fetch_website_metadata(url)
        if meta.get("title"):
            data["title"] = meta["title"]
        if meta.get("description") and not text:
            data["description"] = meta["description"]
        if meta.get("thumbnail") and not image:
            data["thumbnail"] = meta["thumbnail"]
    if not data["title"]:
        # Fallbacks so the preview is never empty.
        data["title"] = (text.strip().split("\n")[0][:120] if text else "") or (url[:120] if url else "Shared item")
    return data
