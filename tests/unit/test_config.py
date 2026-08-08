import os
from config import Config, ProductionConfig


def test_config_database_uri(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
    assert Config.get_database_uri() == "postgresql://user:pass@host/db"

    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@host/db")
    assert Config.get_database_uri() == "mysql://user:pass@host/db"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Config.get_database_uri() is None


def test_production_csp_allows_icon_and_google_fonts():
    """Production CSP must permit the bootstrap-icons (CDN) and Google Fonts
    font sources, or every 'bi' icon on the site renders as an empty box."""
    csp = ProductionConfig.SECURITY_HEADERS["Content-Security-Policy"]
    assert "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net" in csp

