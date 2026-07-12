import os
from config import Config

def test_config_database_uri(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
    assert Config.get_database_uri() == "postgresql://user:pass@host/db"

    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@host/db")
    assert Config.get_database_uri() == "mysql://user:pass@host/db"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Config.get_database_uri() is None
