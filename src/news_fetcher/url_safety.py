"""
URL safety: allowlist schemes and block private/localhost to prevent
malicious or SSRF URLs from entering the project (config, feeds, output, .seen_urls).
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# Only these schemes are allowed. Blocks file:, javascript:, data:, etc.
ALLOWED_SCHEMES = frozenset({"https", "http"})

# Hostnames that must not be used (case-insensitive).
BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "::1",
})


def _host_is_blocked_name(host: str) -> bool:
    """Return True if host is a blocked hostname (e.g. localhost)."""
    if not host:
        return True
    lower = host.lower().strip()
    if lower in BLOCKED_HOSTNAMES:
        return True
    if lower.endswith(".local"):
        return True
    if lower.endswith(".localhost"):
        return True
    return False


def _host_is_private_ip(host: str) -> bool:
    """Return True if host is a literal private/loopback/link-local IP."""
    if not host:
        return True
    host = host.strip()
    # Strip brackets for IPv6 in URL, e.g. [::1]
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False  # not an IP, will be checked as hostname
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_reserved  # e.g. 0.0.0.0/8, 100.64.0.0/10
    )


def is_safe_url(url: str, *, https_only: bool = False) -> bool:
    """
    Return True if the URL is safe to fetch or to store (verified URL only).
    - Scheme must be in ALLOWED_SCHEMES (https, http). If https_only, only https.
    - Host must not be localhost or private/link-local/reserved IP.
    - No newlines or obvious injection in the URL string.
    """
    if not url or not isinstance(url, str):
        return False
    s = url.strip()
    # Reject URLs with newlines (injection in .seen_urls or logs).
    if "\n" in s or "\r" in s:
        return False
    try:
        parsed = urlparse(s)
    except (ValueError, TypeError, AttributeError):
        return False
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        return False
    if https_only and scheme != "https":
        return False
    netloc = (parsed.netloc or "").strip()
    if not netloc:
        return False
    # Host part (no port for the safety check; port is allowed in netloc).
    host = netloc.split(":")[0] if ":" in netloc else netloc
    if _host_is_blocked_name(host):
        return False
    if _host_is_private_ip(host):
        return False
    return True


def is_safe_feed_url(url: str) -> bool:
    """Strict: only HTTPS feed URLs (for config sources)."""
    return is_safe_url(url, https_only=True)


def is_safe_article_url(url: str) -> bool:
    """Allow https and http for article links; same host/SSRF rules."""
    return is_safe_url(url, https_only=False)
