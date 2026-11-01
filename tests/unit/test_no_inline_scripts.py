"""Regression tests: no template may rely on inline script.

The production Content-Security-Policy (script-src 'self'
https://cdn.jsdelivr.net, no 'unsafe-inline') silently disables every
inline <script> block, inline on* event-handler attribute, and
javascript: URL, while every other environment lets them run — so the
failure is invisible to request/response tests. These tests scan the
template sources directly and pin the external replacements.

# @spec GIV-CLM-021
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"
STATIC_JS = REPO_ROOT / "static" / "js"

SCRIPT_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
# An attribute name starting with "on", not preceded by a word character or
# a hyphen (so hx-on / data-onclick never match), wherever it appears —
# including immediately after a Jinja tag ({% ... %}onclick=), which still
# renders as a real attribute.
INLINE_HANDLER = re.compile(r"(?<![\w-])on[a-z]+\s*=", re.IGNORECASE)
JAVASCRIPT_URL = re.compile(r"""(?:href|action)\s*=\s*["']\s*javascript:""",
                            re.IGNORECASE)


def _template_files():
    return sorted(TEMPLATES.rglob("*.html"))


def _scan():
    """Collect every inline-script violation as 'file:line: detail'."""
    violations = []
    for path in _template_files():
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for tag in SCRIPT_TAG.findall(line):
                if "src=" not in tag:
                    violations.append(
                        f"{rel}:{lineno}: inline <script> block {tag!r}")
            for attr in INLINE_HANDLER.findall(line):
                violations.append(
                    f"{rel}:{lineno}: inline event handler {attr.strip()!r}")
            if JAVASCRIPT_URL.search(line):
                violations.append(f"{rel}:{lineno}: javascript: URL")
    return violations


def test_templates_contain_no_inline_script():
    # @spec GIV-CLM-021
    violations = _scan()
    assert not violations, (
        "inline script is blocked by the production CSP; externalize it:\n"
        + "\n".join(violations)
    )


def test_service_worker_registration_is_external(client):
    # @spec GIV-CLM-021
    html = client.get("/login").get_data(as_text=True)
    assert "js/sw-register.js" in html
    js = (STATIC_JS / "sw-register.js").read_text()
    assert "serviceWorker" in js
    assert "currentScript" in js, "the SW URL must arrive via data attribute"


def test_app_behaviors_script_is_loaded_and_wired(client):
    # @spec GIV-CLM-021
    html = client.get("/login").get_data(as_text=True)
    assert "js/app-behaviors.js" in html
    js = (STATIC_JS / "app-behaviors.js").read_text()
    for hook in ("data-confirm-message", "data-item-form",
                 "js-split-amount", "js-img-fallback", "js-history-back"):
        assert hook in js, f"app-behaviors.js must wire {hook}"


def test_feature_scripts_exist_with_their_hooks():
    # @spec GIV-CLM-021
    expectations = {
        "item-form.js": ("autofill-btn", "/api/fetch-metadata"),
        "notifications.js": ("data-mark-read-url", "sendBeacon"),
        "items-list.js": ("show.bs.collapse", "hide.bs.collapse"),
    }
    for filename, needles in expectations.items():
        path = STATIC_JS / filename
        assert path.exists(), f"static/js/{filename} is missing"
        body = path.read_text()
        for needle in needles:
            assert needle in body, f"{filename} must contain {needle}"


def test_templates_reference_the_external_replacements():
    # @spec GIV-CLM-021
    sources = {
        "submit_item.html": "js/item-form.js",
        "edit_item.html": "js/item-form.js",
        "notifications.html": "js/notifications.js",
        "items_list.html": "js/items-list.js",
    }
    for template, script in sources.items():
        body = (TEMPLATES / template).read_text()
        assert script in body, f"{template} must load {script}"

    notifications = (TEMPLATES / "notifications.html").read_text()
    assert "data-mark-read-url" in notifications

    split_modal = (TEMPLATES / "partials" / "_split_modal.html").read_text()
    assert "js-split-amount" in split_modal
    assert "data-confirm-message" in split_modal

    item_card = (TEMPLATES / "partials" / "_item_card.html").read_text()
    assert "data-confirm-message" in item_card

    events = (TEMPLATES / "events.html").read_text()
    assert "data-confirm-message" in events

    quick_view = (TEMPLATES / "partials" / "_item_quick_view.html").read_text()
    assert "js-img-fallback" in quick_view

    not_found = (TEMPLATES / "errors" / "404.html").read_text()
    assert "js-history-back" in not_found
