"""Regression tests: HTMX delivery must survive the production CSP.

Production serves script-src 'self' https://cdn.jsdelivr.net with no
'unsafe-inline'. HTMX actions (claim/unclaim, split, quick view) only work
if the library loads from an allowed origin and the CSRF header wiring is
itself CSP-compliant. These tests pin that contract against the real base
template and the real ProductionConfig policy.

# @spec GIV-CLM-018, GIV-CLM-019
"""
import re
from pathlib import Path
from urllib.parse import urlparse

from config import ProductionConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_TEMPLATE = REPO_ROOT / "templates" / "base.html"
HTMX_CSRF_JS = REPO_ROOT / "static" / "js" / "htmx-csrf.js"


def _script_src_allowlist():
    """Origins permitted by the production CSP script-src directive."""
    csp = ProductionConfig.SECURITY_HEADERS["Content-Security-Policy"]
    directives = {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}
    return directives["script-src"]


def _external_script_srcs(html):
    return re.findall(r'<script[^>]+src="([^"]+)"', html)


def _origin(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def test_base_template_scripts_allowed_by_production_csp(client):
    # @spec GIV-CLM-018
    allowlist = _script_src_allowlist()
    response = client.get("/login")
    assert response.status_code == 200
    for src in _external_script_srcs(response.get_data(as_text=True)):
        if src.startswith("http://") or src.startswith("https://"):
            assert _origin(src) in allowlist, (
                f"script {src} is not permitted by production script-src {allowlist}"
            )
        # Relative/static URLs are covered by 'self'.


def test_htmx_script_present_with_integrity(client):
    # @spec GIV-CLM-018
    html = client.get("/login").get_data(as_text=True)
    tags = re.findall(r"<script[^>]*htmx[^>]*>", html)
    assert tags, "no HTMX script tag rendered"
    assert any('integrity="sha384-' in tag for tag in tags)


def test_csrf_token_meta_rendered(client):
    # @spec GIV-CLM-019
    html = client.get("/login").get_data(as_text=True)
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    assert match and match.group(1), "csrf-token meta element missing or empty"


def test_no_inline_htmx_csrf_listener_in_base_template():
    # @spec GIV-CLM-019
    source = BASE_TEMPLATE.read_text()
    assert "htmx:configRequest" not in source, (
        "inline htmx:configRequest listener is blocked by CSP; "
        "it must live in an external static script"
    )


def test_htmx_csrf_wiring_is_external_static_script(client):
    # @spec GIV-CLM-019
    html = client.get("/login").get_data(as_text=True)
    assert "js/htmx-csrf.js" in html, "base template must load js/htmx-csrf.js"
    assert HTMX_CSRF_JS.exists(), "static/js/htmx-csrf.js is missing"
    js = HTMX_CSRF_JS.read_text()
    assert "htmx:configRequest" in js
    assert "X-CSRFToken" in js
    assert "csrf-token" in js, "external script must read the token from the meta element"
