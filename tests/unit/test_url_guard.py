"""Tests for the SSRF guard: the URL predicate and redirect-hop enforcement."""

import pytest
import requests

from services import price_service
from services.url_guard import (
    is_enforcing,
    is_public_http_url,
    restrict_outbound_to_public_urls,
)


# --- predicate -------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/latest",
    "http://localhost/admin",
    "http://192.168.1.10/router",
    "http://10.0.0.5/",
    "http://169.254.169.254/latest/meta-data/",   # cloud metadata
    "ftp://example.com/file",
    "file:///etc/passwd",
    "",
    None,
    "not a url",
])
def test_rejects_non_public_targets(url):
    assert is_public_http_url(url) is False


def test_accepts_public_http_url(monkeypatch):
    # Resolve to a public address without touching real DNS.
    monkeypatch.setattr("socket.getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, '', ('93.184.216.34', 80))])
    assert is_public_http_url("https://example.com/product") is True


def test_rejects_host_with_any_private_answer(monkeypatch):
    """Split-horizon DNS must not slip an internal address through."""
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [
        (2, 1, 6, '', ('93.184.216.34', 80)),
        (2, 1, 6, '', ('10.0.0.7', 80)),
    ])
    assert is_public_http_url("https://sneaky.example/x") is False


# --- enforcement context ---------------------------------------------------

def test_enforcement_is_scoped():
    assert is_enforcing() is False
    with restrict_outbound_to_public_urls():
        assert is_enforcing() is True
    assert is_enforcing() is False


# --- redirect-hop validation (the actual SSRF bypass) ----------------------

class FakeResponse:
    def __init__(self, status_code=200, location=None, text="ok"):
        self.status_code = status_code
        self.headers = {"Location": location} if location else {}
        self.text = text
        self.content = text.encode()
        self.ok = status_code < 400
        self.url = ""

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308)

    def raise_for_status(self):
        pass


class FakeSession:
    """Records requested URLs and replays a scripted redirect chain."""

    def __init__(self, script):
        self.script = script
        self.requested = []
        self.headers = {}

    def get(self, url, timeout=None, allow_redirects=False):
        self.requested.append(url)
        return self.script.get(url, FakeResponse())


def test_public_redirect_chain_is_followed(monkeypatch):
    monkeypatch.setattr("services.url_guard.is_public_http_url", lambda url: True)
    session = FakeSession({
        "https://a.co/x": FakeResponse(302, location="https://www.amazon.com/dp/1"),
        "https://www.amazon.com/dp/1": FakeResponse(200, text="product"),
    })

    response = price_service._get_following_validated_redirects(session, "https://a.co/x")

    assert response.text == "product"
    assert session.requested == ["https://a.co/x", "https://www.amazon.com/dp/1"]


def test_redirect_to_internal_address_is_blocked(monkeypatch):
    """The real bypass: a public URL that 302s to the metadata endpoint."""
    monkeypatch.setattr("services.url_guard.is_public_http_url",
                        lambda url: "169.254" not in url and "127.0.0.1" not in url)
    session = FakeSession({
        "https://evil.example/x": FakeResponse(302, location="http://169.254.169.254/latest/meta-data/"),
    })

    with pytest.raises(requests.RequestException, match="Blocked non-public URL"):
        price_service._get_following_validated_redirects(session, "https://evil.example/x")

    # The internal address was never actually fetched.
    assert session.requested == ["https://evil.example/x"]


def test_redirect_loop_gives_up(monkeypatch):
    monkeypatch.setattr("services.url_guard.is_public_http_url", lambda url: True)
    session = FakeSession({
        "https://loop.example/a": FakeResponse(302, location="https://loop.example/a"),
    })

    with pytest.raises(requests.RequestException, match="Too many redirects"):
        price_service._get_following_validated_redirects(session, "https://loop.example/a")


def test_make_request_only_validates_when_enforcing(monkeypatch):
    """Website behavior is unchanged: redirects are followed by requests itself."""
    monkeypatch.setattr(price_service.price_cache, "get_cached_response", lambda url: None)
    monkeypatch.setattr(price_service.price_cache, "cache_response", lambda url, text: None)

    calls = {}

    class RecordingSession:
        headers = {}

        def get(self, url, timeout=None, allow_redirects=None):
            calls["allow_redirects"] = allow_redirects
            return FakeResponse(200, text="page")

    monkeypatch.setattr(price_service, "_get_session", lambda: RecordingSession())

    # Not enforcing (web path): hands redirect-following to requests.
    price_service._make_request("https://example.com/p")
    assert calls["allow_redirects"] is True

    # Enforcing (API path): fetches one hop at a time instead.
    calls.clear()
    monkeypatch.setattr("services.url_guard.is_public_http_url", lambda url: True)
    with restrict_outbound_to_public_urls():
        price_service._make_request("https://example.com/p")
    assert calls["allow_redirects"] is False


# --- host matching (py/incomplete-url-substring-sanitization) ---------------

@pytest.mark.parametrize("domain", [
    "amazon.com", "www.amazon.com", "smile.amazon.com", "amazon.co.uk",
    "amazon.com.au", "a.co", "amzn.to",
])
def test_amazon_hosts_match(domain):
    assert price_service._host_matches(domain, price_service.AMAZON_HOSTS) is True


@pytest.mark.parametrize("domain", [
    "amazon.evil.com",        # substring check would wrongly match this
    "notamazon.com",
    "amazon.com.evil.net",
    "target.com.evil.net",
    "myamazon.org",
    "",
    None,
])
def test_lookalike_hosts_do_not_match(domain):
    assert price_service._host_matches(domain, price_service.AMAZON_HOSTS) is False


def test_target_host_matching():
    assert price_service._host_matches("www.target.com", price_service.TARGET_HOSTS) is True
    assert price_service._host_matches("target.com.evil.net", price_service.TARGET_HOSTS) is False


def test_host_matching_ignores_port_and_trailing_dot():
    assert price_service._host_matches("www.amazon.com:443", price_service.AMAZON_HOSTS) is True
    assert price_service._host_matches("amazon.com.", price_service.AMAZON_HOSTS) is True
