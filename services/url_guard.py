"""SSRF guard for outbound fetches of user-supplied URLs.

Validating the URL a user submits is not enough: an attacker can host a
public URL that 302-redirects to an internal address (``127.0.0.1``,
``169.254.169.254``, RFC1918 …), and a naive fetcher follows it. So the
guard has two halves:

* :func:`is_public_http_url` — the predicate (scheme + resolved-IP check).
* :func:`restrict_outbound_to_public_urls` — a context manager that turns on
  *enforcement* for the current task/thread. While enforcing,
  ``price_service._make_request`` follows redirects one hop at a time and
  re-checks every hop.

Enforcement is opt-in so the website's existing price fetching is unchanged
(it relies on redirects for short links like ``a.co``/``amzn.to``); the
token-authenticated API opts in for URLs supplied by API clients.
"""

import socket
from contextlib import contextmanager
from contextvars import ContextVar
from ipaddress import ip_address
from urllib.parse import urlparse

# True while an outbound fetch must be restricted to public URLs.
_enforcing = ContextVar('ssrf_enforcing', default=False)

# Redirect hops to follow before giving up (short links can chain a few).
MAX_REDIRECT_HOPS = 5


def is_public_http_url(url):
    """Return True for absolute http(s) URLs on globally-routable hosts.

    Rejects non-http schemes, unresolvable hosts, and any host that resolves
    to a non-global address — loopback, RFC1918, link-local (including the
    cloud metadata endpoint), multicast, and reserved space. A host with
    *any* non-global answer is rejected, so a split-horizon DNS record can't
    sneak an internal address through.
    """
    if not url or not isinstance(url, str):
        return False

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False

    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80,
                                   proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, ValueError):
        return False
    if not infos:
        return False

    for info in infos:
        try:
            addr = ip_address(info[4][0])
        except ValueError:
            return False
        if not addr.is_global or addr.is_multicast:
            return False
    return True


@contextmanager
def restrict_outbound_to_public_urls():
    """Enforce :func:`is_public_http_url` on fetches made inside this block."""
    token = _enforcing.set(True)
    try:
        yield
    finally:
        _enforcing.reset(token)


def is_enforcing():
    """Whether outbound fetches in the current context must be public-only."""
    return _enforcing.get()
